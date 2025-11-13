"""Robot 1: Horizon Scanner - Discovers trending seed topics."""

import logging
import asyncio
import os
import math
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from pytrends.request import TrendReq
import praw
from datetime import datetime

from src.models.seed_topic import SeedTopic, SourceType, TrendStatus
from src.models.niche_config import NicheConfig
from src.models.job_status import JobStatus
from src.services.config_manager import ConfigManager
from src.config.settings import settings
from src.services.event_manager import (
    broadcast_job_started,
    broadcast_job_progress,
    broadcast_job_completed,
    broadcast_job_failed,
    broadcast_topic_discovered,
    broadcast_robot_status
)

logger = logging.getLogger(__name__)


class HorizonScanner:
    """
    Robot 1: Horizon Scanner

    Discovers trending "seed topics" from:
    - Google Trends (pytrends) - Currently has 404 errors
    - Reddit (praw) - Working

    These seed topics will be used by Robot 2 to search for YouTube videos.

    Now integrated with:
    - Database-first configuration (NicheConfig model)
    - ConfigManager for settings
    - JobStatus for progress tracking
    - EventManager for real-time updates
    """

    def __init__(self, db_session: Session):
        """
        Initialize Horizon Scanner.

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.config_manager = ConfigManager(db_session)
        self.google_trends_client: Optional[TrendReq] = None
        self.reddit_client: Optional[praw.Reddit] = None
        self.job_id: Optional[int] = None

    def _get_credential(self, db_key: str, env_value: Optional[str], name: str) -> Optional[str]:
        """
        Get credential with proper fallback logic.

        Priority:
        1. Database (if set and non-empty)
        2. Environment variable (from .env via settings)

        Args:
            db_key: Database key (e.g., 'reddit.client_id')
            env_value: Value from settings/environment
            name: Human-readable name for logging

        Returns:
            Credential value or None
        """
        # Try database first
        db_value = self.config_manager.get(db_key, None, 'api_keys')

        # Use database value if it exists and is non-empty
        if db_value and isinstance(db_value, str) and db_value.strip():
            logger.info(f"{name} loaded from database")
            return db_value.strip()

        # Fall back to environment
        if env_value and isinstance(env_value, str) and env_value.strip():
            logger.info(f"{name} loaded from environment (.env)")
            return env_value.strip()

        # Not found in either location
        return None

    def _init_google_trends(self):
        """Initialize Google Trends client."""
        enabled = self.config_manager.get('robot1.google_trends.enabled', True, 'robot1')

        if not enabled:
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
        enabled = self.config_manager.get('robot1.reddit.enabled', True, 'robot1')

        if not enabled:
            logger.warning("Reddit disabled in settings")
            return

        # Get credentials using standardized helper with proper empty-string handling
        client_id = self._get_credential('reddit.client_id', settings.REDDIT_CLIENT_ID, 'Reddit Client ID')
        client_secret = self._get_credential('reddit.client_secret', settings.REDDIT_CLIENT_SECRET, 'Reddit Client Secret')
        user_agent = self._get_credential('reddit.user_agent', settings.REDDIT_USER_AGENT, 'Reddit User Agent')

        if not client_id or not client_secret:
            logger.warning("Reddit credentials not configured")
            return

        try:
            self.reddit_client = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
            )
            logger.info("Reddit client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit: {e}")
            self.reddit_client = None

    async def run(self, niche_id: int, max_topics: Optional[int] = None) -> Dict:
        """
        Run the Horizon Scanner for a specific niche.

        Args:
            niche_id: ID of the niche configuration in database
            max_topics: Maximum number of topics to discover (optional)

        Returns:
            Dict with scan results
        """
        logger.info(f"Starting Horizon Scanner for niche ID: {niche_id}")

        # Load niche configuration from database
        stmt = select(NicheConfig).where(
            NicheConfig.id == niche_id,
            NicheConfig.is_active == 1
        )
        niche_config = self.db.execute(stmt).scalar_one_or_none()

        if not niche_config:
            raise ValueError(f"Niche configuration not found or inactive: ID {niche_id}")

        # Get max topics from ConfigManager if not specified
        if max_topics is None:
            max_topics = self.config_manager.get('robot1.max_topics_per_run', 50, 'robot1')

        # Create job status record
        job = JobStatus(
            job_type='robot1',
            status='running',
            config_snapshot={
                'niche_id': niche_id,
                'niche_name': niche_config.niche_name,
                'max_topics': max_topics,
                'google_trends_enabled': niche_config.google_trends_weight > 0,
                'reddit_enabled': niche_config.reddit_weight > 0
            }
        )
        job.start()
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        self.job_id = job.id

        try:
            # Broadcast job started event
            await broadcast_job_started(
                job_id=job.id,
                job_type='robot1',
                niche_name=niche_config.niche_name,
                niche_id=niche_id
            )

            # Broadcast robot status
            await broadcast_robot_status(
                robot='robot1',
                status='running',
                niche=niche_config.niche_name
            )

            # Update progress: Initializing
            job.update_progress(5, "Initializing clients")
            self.db.commit()
            await broadcast_job_progress(job.id, 5, "Initializing clients")

            # Initialize clients
            self._init_google_trends()
            self._init_reddit()

            topics_found = []

            # Update progress: Scanning sources
            job.update_progress(10, "Scanning data sources")
            self.db.commit()
            await broadcast_job_progress(job.id, 10, "Scanning data sources")

            # Scan Google Trends
            if niche_config.google_trends_weight > 0 and self.google_trends_client:
                job.update_progress(15, "Scanning Google Trends")
                self.db.commit()
                await broadcast_job_progress(job.id, 15, "Scanning Google Trends")

                logger.info("Scanning Google Trends...")
                trends_topics = await self._scan_google_trends(niche_config)
                topics_found.extend(trends_topics)
                logger.info(f"Found {len(trends_topics)} topics from Google Trends")

                job.update_progress(45, f"Found {len(trends_topics)} topics from Google Trends")
                self.db.commit()
                await broadcast_job_progress(job.id, 45, f"Found {len(trends_topics)} topics from Google Trends")

            # Scan Reddit
            if niche_config.reddit_weight > 0 and self.reddit_client:
                job.update_progress(50, "Scanning Reddit")
                self.db.commit()
                await broadcast_job_progress(job.id, 50, "Scanning Reddit")

                logger.info("Scanning Reddit...")
                reddit_topics = await self._scan_reddit(niche_config)
                topics_found.extend(reddit_topics)
                logger.info(f"Found {len(reddit_topics)} topics from Reddit")

                job.update_progress(70, f"Found {len(reddit_topics)} topics from Reddit")
                self.db.commit()
                await broadcast_job_progress(job.id, 70, f"Found {len(reddit_topics)} topics from Reddit")

            # Save topics to database
            job.update_progress(85, "Saving topics to database")
            self.db.commit()
            await broadcast_job_progress(job.id, 85, "Saving topics to database")

            saved_count = await self._save_topics(topics_found, niche_config.niche_name, max_topics)

            # Complete the job
            job.update_progress(100, "Completed")
            result_summary = {
                "topics_found": len(topics_found),
                "topics_saved": saved_count,
                "google_trends": len([t for t in topics_found if t["source"] == SourceType.GOOGLE_TRENDS]),
                "reddit": len([t for t in topics_found if t["source"] == SourceType.REDDIT])
            }
            job.complete(result_summary=result_summary)
            self.db.commit()

            logger.info(f"Horizon Scanner completed. Saved {saved_count} topics.")

            # Broadcast completion
            await broadcast_job_completed(
                job_id=job.id,
                result_summary=result_summary
            )

            await broadcast_robot_status(
                robot='robot1',
                status='idle',
                last_run_result=result_summary
            )

            return {
                "status": "completed",
                "job_id": job.id,
                "niche": niche_config.niche_name,
                **result_summary
            }

        except Exception as e:
            logger.error(f"Error in Horizon Scanner: {e}", exc_info=True)

            # Mark job as failed
            if job:
                job.fail(error_message=str(e))
                self.db.commit()

                await broadcast_job_failed(
                    job_id=job.id,
                    error=str(e)
                )

                await broadcast_robot_status(
                    robot='robot1',
                    status='error',
                    error=str(e)
                )

            raise

    async def _scan_google_trends(self, config: NicheConfig) -> List[Dict]:
        """
        Scan Google Trends for trending topics.

        Args:
            config: Niche configuration from database

        Returns:
            List of discovered topics
        """
        topics = []

        try:
            # Get region from config or default
            # Note: In the new system, we'll add region support to NicheConfig model
            region = "US"  # Default for now

            # Get trending searches
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
            min_trend_score = config.min_search_volume / 1000  # Rough approximation

            if config.keywords:
                for keyword in config.keywords[:5]:  # Limit to avoid rate limiting
                    try:
                        self.google_trends_client.build_payload([keyword], timeframe='now 7-d')
                        interest = self.google_trends_client.interest_over_time()

                        if not interest.empty and keyword in interest.columns:
                            latest_score = float(interest[keyword].iloc[-1])

                            if latest_score > min_trend_score:
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

                                # Broadcast topic discovered
                                if self.job_id:
                                    await broadcast_topic_discovered(
                                        topic=keyword,
                                        source="google_trends",
                                        trend_score=latest_score,
                                        job_id=self.job_id
                                    )

                    except Exception as e:
                        logger.warning(f"Error getting trends for keyword '{keyword}': {e}")
                        continue

        except Exception as e:
            logger.error(f"Error scanning Google Trends: {e}", exc_info=True)

        return topics

    async def _scan_reddit(self, config: NicheConfig) -> List[Dict]:
        """
        Scan Reddit for trending topics.

        Args:
            config: Niche configuration from database

        Returns:
            List of discovered topics
        """
        topics = []

        try:
            # Get subreddits from niche configuration
            subreddits = config.reddit_subreddits if config.reddit_subreddits else []

            # Default subreddits if none specified
            if not subreddits:
                subreddits = ['all']

            # Get min upvotes from ConfigManager
            min_upvotes = self.config_manager.get('robot1.reddit.min_upvotes', 50, 'robot1')
            time_filter = self.config_manager.get('robot1.reddit.time_filter', 'week', 'robot1')

            for subreddit_name in subreddits[:10]:  # Limit subreddits to avoid rate limiting
                try:
                    subreddit = self.reddit_client.subreddit(subreddit_name)

                    # Get hot posts
                    for post in subreddit.hot(limit=25):
                        if post.score >= min_upvotes and not post.stickied:
                            # Logarithmic scoring: 50 upvotes=30, 500=65, 5000=95, 50000=100
                            score_ratio = max(1, post.score / min_upvotes)
                            reddit_score = min(100.0, 30 + (math.log10(score_ratio) * 35))

                            topic_data = {
                                "topic": post.title,
                                "source": SourceType.REDDIT,
                                "trend_score": reddit_score,
                                "trend_status": TrendStatus.PEAK if post.score > min_upvotes * 10 else TrendStatus.RISING,
                                "source_url": f"https://reddit.com{post.permalink}",
                                "source_metadata": {
                                    "subreddit": subreddit_name,
                                    "upvotes": post.score,
                                    "comments": post.num_comments,
                                    "post_type": "hot"
                                }
                            }
                            topics.append(topic_data)

                            # Broadcast topic discovered
                            if self.job_id:
                                await broadcast_topic_discovered(
                                    topic=post.title[:100],  # Truncate for event
                                    source="reddit",
                                    trend_score=topic_data["trend_score"],
                                    subreddit=subreddit_name,
                                    job_id=self.job_id
                                )

                    # Get top posts
                    for post in subreddit.top(time_filter=time_filter, limit=25):
                        if post.score >= min_upvotes and not post.stickied:
                            # Logarithmic scoring: 50 upvotes=30, 500=65, 5000=95, 50000=100
                            score_ratio = max(1, post.score / min_upvotes)
                            reddit_score = min(100.0, 30 + (math.log10(score_ratio) * 35))

                            topics.append({
                                "topic": post.title,
                                "source": SourceType.REDDIT,
                                "trend_score": reddit_score,
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

    async def _save_topics(self, topics: List[Dict], niche: str, max_topics: int) -> int:
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
