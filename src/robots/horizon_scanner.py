"""Robot 1: Horizon Scanner - Discovers trending seed topics."""

import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from pytrends.request import TrendReq
import praw
from datetime import datetime
from src.models.seed_topic import SeedTopic, SourceType, TrendStatus
from src.config.niche_loader import niche_loader, NicheConfig
from src.config.settings import settings

logger = logging.getLogger(__name__)


class HorizonScanner:
    """
    Robot 1: Horizon Scanner

    Discovers trending "seed topics" from:
    - Google Trends (pytrends)
    - Reddit (praw)

    These seed topics will be used by Robot 2 to search for YouTube videos.
    """

    def __init__(self, db_session: Session):
        """
        Initialize Horizon Scanner.

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.google_trends_client: Optional[TrendReq] = None
        self.reddit_client: Optional[praw.Reddit] = None

    def _init_google_trends(self):
        """Initialize Google Trends client."""
        if not settings.ROBOT1_GOOGLE_TRENDS_ENABLED:
            logger.warning("Google Trends disabled in settings")
            return

        try:
            self.google_trends_client = TrendReq(hl='en-US', tz=360)
            logger.info("Google Trends client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Trends: {e}")
            self.google_trends_client = None

    def _init_reddit(self):
        """Initialize Reddit client."""
        if not settings.ROBOT1_REDDIT_ENABLED:
            logger.warning("Reddit disabled in settings")
            return

        if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
            logger.warning("Reddit credentials not configured")
            return

        try:
            self.reddit_client = praw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT,
            )
            logger.info("Reddit client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit: {e}")
            self.reddit_client = None

    def run(self, niche_name: str, max_topics: Optional[int] = None) -> Dict:
        """
        Run the Horizon Scanner for a specific niche.

        Args:
            niche_name: Name of the niche to scan
            max_topics: Maximum number of topics to discover (optional)

        Returns:
            Dict with scan results
        """
        logger.info(f"Starting Horizon Scanner for niche: {niche_name}")

        # Load niche configuration
        config = niche_loader.get_config(niche_name)
        if not config:
            raise ValueError(f"Niche configuration not found: {niche_name}")

        max_topics = max_topics or settings.ROBOT1_MAX_TOPICS_PER_RUN

        # Initialize clients
        self._init_google_trends()
        self._init_reddit()

        topics_found = []

        # Scan Google Trends
        if config.google_trends.get("enabled", True) and self.google_trends_client:
            logger.info("Scanning Google Trends...")
            trends_topics = self._scan_google_trends(config)
            topics_found.extend(trends_topics)
            logger.info(f"Found {len(trends_topics)} topics from Google Trends")

        # Scan Reddit
        if config.reddit.get("enabled", True) and self.reddit_client:
            logger.info("Scanning Reddit...")
            reddit_topics = self._scan_reddit(config)
            topics_found.extend(reddit_topics)
            logger.info(f"Found {len(reddit_topics)} topics from Reddit")

        # Save topics to database
        saved_count = self._save_topics(topics_found, niche_name, max_topics)

        logger.info(f"Horizon Scanner completed. Saved {saved_count} topics.")

        return {
            "status": "completed",
            "niche": niche_name,
            "topics_found": len(topics_found),
            "topics_saved": saved_count,
            "google_trends": len([t for t in topics_found if t["source"] == SourceType.GOOGLE_TRENDS]),
            "reddit": len([t for t in topics_found if t["source"] == SourceType.REDDIT]),
        }

    def _scan_google_trends(self, config: NicheConfig) -> List[Dict]:
        """
        Scan Google Trends for trending topics.

        Args:
            config: Niche configuration

        Returns:
            List of discovered topics
        """
        topics = []

        try:
            # Get trending searches
            region = config.google_trends.get("region", "US")
            trending = self.google_trends_client.trending_searches(pn=region)

            for topic in trending[0][:20]:  # Top 20 trending
                topics.append({
                    "topic": topic,
                    "source": SourceType.GOOGLE_TRENDS,
                    "trend_score": 100.0,  # Trending searches are high priority
                    "trend_status": TrendStatus.RISING,
                    "source_metadata": {
                        "region": region,
                        "type": "trending_search"
                    }
                })

            # Get interest over time for keywords
            if config.keywords:
                for keyword in config.keywords[:5]:  # Limit to avoid rate limiting
                    try:
                        self.google_trends_client.build_payload([keyword], timeframe='now 7-d')
                        interest = self.google_trends_client.interest_over_time()

                        if not interest.empty and keyword in interest.columns:
                            latest_score = float(interest[keyword].iloc[-1])

                            if latest_score > config.min_trend_score:
                                topics.append({
                                    "topic": keyword,
                                    "source": SourceType.GOOGLE_TRENDS,
                                    "trend_score": latest_score,
                                    "trend_status": self._determine_trend_status(interest[keyword]),
                                    "source_metadata": {
                                        "region": region,
                                        "type": "keyword_search",
                                        "timeframe": "7d"
                                    }
                                })
                    except Exception as e:
                        logger.warning(f"Error getting trends for keyword '{keyword}': {e}")
                        continue

        except Exception as e:
            logger.error(f"Error scanning Google Trends: {e}", exc_info=True)

        return topics

    def _scan_reddit(self, config: NicheConfig) -> List[Dict]:
        """
        Scan Reddit for trending topics.

        Args:
            config: Niche configuration

        Returns:
            List of discovered topics
        """
        topics = []

        try:
            subreddits = config.reddit.get("subreddits", [])
            min_upvotes = config.reddit.get("min_upvotes", 50)
            time_filter = config.reddit.get("time_filter", "week")

            for subreddit_name in subreddits:
                try:
                    subreddit = self.reddit_client.subreddit(subreddit_name)

                    # Get hot posts
                    for post in subreddit.hot(limit=25):
                        if post.score >= min_upvotes and not post.stickied:
                            topics.append({
                                "topic": post.title,
                                "source": SourceType.REDDIT,
                                "trend_score": min(100.0, (post.score / min_upvotes) * 50),
                                "trend_status": TrendStatus.PEAK if post.score > min_upvotes * 10 else TrendStatus.RISING,
                                "source_url": f"https://reddit.com{post.permalink}",
                                "source_metadata": {
                                    "subreddit": subreddit_name,
                                    "upvotes": post.score,
                                    "comments": post.num_comments,
                                    "post_type": "hot"
                                }
                            })

                    # Get top posts
                    for post in subreddit.top(time_filter=time_filter, limit=25):
                        if post.score >= min_upvotes and not post.stickied:
                            topics.append({
                                "topic": post.title,
                                "source": SourceType.REDDIT,
                                "trend_score": min(100.0, (post.score / min_upvotes) * 50),
                                "trend_status": TrendStatus.PEAK,
                                "source_url": f"https://reddit.com{post.permalink}",
                                "source_metadata": {
                                    "subreddit": subreddit_name,
                                    "upvotes": post.score,
                                    "comments": post.num_comments,
                                    "post_type": "top",
                                    "time_filter": time_filter
                                }
                            })

                except Exception as e:
                    logger.warning(f"Error scanning subreddit r/{subreddit_name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error scanning Reddit: {e}", exc_info=True)

        return topics

    def _determine_trend_status(self, series) -> TrendStatus:
        """
        Determine trend status from time series data.

        Args:
            series: Pandas series of trend values

        Returns:
            TrendStatus enum
        """
        if len(series) < 2:
            return TrendStatus.STABLE

        recent_avg = series[-3:].mean()
        previous_avg = series[-7:-3].mean() if len(series) >= 7 else series[:3].mean()

        if recent_avg > previous_avg * 1.2:
            return TrendStatus.RISING
        elif recent_avg < previous_avg * 0.8:
            return TrendStatus.DECLINING
        elif recent_avg > 80:
            return TrendStatus.PEAK
        else:
            return TrendStatus.STABLE

    def _save_topics(self, topics: List[Dict], niche: str, max_topics: int) -> int:
        """
        Save discovered topics to database.

        Args:
            topics: List of topic dictionaries
            niche: Niche name
            max_topics: Maximum topics to save

        Returns:
            Number of topics saved
        """
        # Sort by trend score (descending)
        topics.sort(key=lambda x: x.get("trend_score", 0), reverse=True)

        saved_count = 0

        for topic_data in topics[:max_topics]:
            try:
                # Check if topic already exists
                existing = self.db.query(SeedTopic).filter(
                    SeedTopic.topic == topic_data["topic"],
                    SeedTopic.source == topic_data["source"],
                    SeedTopic.niche == niche
                ).first()

                if existing:
                    # Update existing topic
                    existing.trend_score = topic_data.get("trend_score")
                    existing.trend_status = topic_data.get("trend_status", TrendStatus.STABLE)
                    existing.source_metadata = topic_data.get("source_metadata")
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new topic
                    seed_topic = SeedTopic(
                        topic=topic_data["topic"],
                        source=topic_data["source"],
                        niche=niche,
                        trend_score=topic_data.get("trend_score"),
                        trend_status=topic_data.get("trend_status", TrendStatus.STABLE),
                        source_url=topic_data.get("source_url"),
                        source_metadata=topic_data.get("source_metadata"),
                        keywords=topic_data.get("keywords"),
                        processed=0,
                    )
                    self.db.add(seed_topic)

                saved_count += 1

            except Exception as e:
                logger.error(f"Error saving topic '{topic_data.get('topic')}': {e}")
                continue

        # Commit all changes
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Error committing topics to database: {e}")
            self.db.rollback()
            raise

        return saved_count
