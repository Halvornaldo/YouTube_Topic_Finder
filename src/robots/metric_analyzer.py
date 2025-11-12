"""Robot 3: Metric Analyzer - Analyzes video metrics and calculates opportunity scores."""

import logging
import asyncio
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, join
from datetime import datetime
import time
import json

from src.models.video import Video
from src.models.video_metric import VideoMetric
from src.models.opportunity_score import OpportunityScore, CompetitionLevel
from src.models.search_query import SearchQuery
from src.models.seed_topic import SeedTopic
from src.models.job_status import JobStatus
from src.services.config_manager import ConfigManager
from src.services.metric_analyzer_service import MetricAnalyzerService
from src.services.event_manager import (
    broadcast_job_started,
    broadcast_job_progress,
    broadcast_job_completed,
    broadcast_job_failed,
    broadcast_robot_status
)

logger = logging.getLogger(__name__)


class MetricAnalyzer:
    """
    Robot 3: Metric Analyzer

    Analyzes video metrics by:
    - Taking unanalyzed videos from Robot 2
    - Fetching detailed metrics from YouTube Data API
    - Fetching search volume from Google Ads API (optional)
    - Calculating engagement and velocity metrics
    - Calculating 6 component scores (search volume, competition, velocity, engagement, sentiment, recency)
    - Calculating overall opportunity score (weighted average)
    - Determining competition level and content gaps
    - Predicting trend direction

    Integrated with:
    - ConfigManager for settings
    - JobStatus for progress tracking
    - EventManager for real-time updates
    """

    def __init__(self, db_session: Session):
        """
        Initialize Metric Analyzer.

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.config_manager = ConfigManager(db_session)
        self.youtube_client = None
        self.google_ads_client = None
        self.service = None
        self.job_id: Optional[int] = None

    async def run(
        self,
        video_ids: Optional[List[int]] = None,
        search_query_id: Optional[int] = None,
        seed_topic_id: Optional[int] = None,
        niche: Optional[str] = None,
        batch_size: Optional[int] = None,
        reanalyze: bool = False
    ) -> Dict:
        """
        Run the Metric Analyzer with hybrid video selection.

        Args:
            video_ids: Specific video IDs to analyze (optional)
            search_query_id: Filter by search query ID (optional)
            seed_topic_id: Filter by seed topic ID (optional)
            niche: Filter by niche name (optional)
            batch_size: Maximum videos to process (optional, uses config default)
            reanalyze: Re-analyze already processed videos (default: False)

        Returns:
            Dict with analysis results
        """
        logger.info("Starting Metric Analyzer")

        # Get configuration
        if batch_size is None:
            batch_size = self.config_manager.get('robot3.batch_size', 50, 'robot3')

        # Build query with hybrid filters
        videos = await self._build_video_query(
            video_ids=video_ids,
            search_query_id=search_query_id,
            seed_topic_id=seed_topic_id,
            niche=niche,
            batch_size=batch_size,
            reanalyze=reanalyze
        )

        if not videos:
            logger.warning("No videos found matching the criteria")
            return {
                "status": "completed",
                "message": "No videos found to analyze",
                "videos_analyzed": 0
            }

        logger.info(f"Found {len(videos)} videos to analyze")

        # Create job status record
        job = JobStatus(
            job_type='robot3',
            status='running',
            config_snapshot={
                'video_ids': video_ids,
                'search_query_id': search_query_id,
                'seed_topic_id': seed_topic_id,
                'niche': niche,
                'batch_size': batch_size,
                'reanalyze': reanalyze,
                'videos_found': len(videos)
            },
            progress_percent=0,
            current_step='Initializing'
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        self.job_id = job.id

        # Broadcast job started
        await broadcast_job_started(self.job_id, 'robot3', f"Analyzing {len(videos)} videos")
        await broadcast_robot_status('robot3', 'running', f"Processing {len(videos)} videos")

        try:
            # Initialize API clients
            await self._initialize_clients()

            # Process videos
            result = await self._process_videos(videos)

            # Update job status
            job.status = 'completed'
            job.progress_percent = 100
            job.current_step = 'Completed'
            job.completed_at = datetime.utcnow()
            job.result_summary = result
            self.db.commit()

            # Broadcast completion
            await broadcast_job_completed(
                self.job_id,
                'robot3',
                f"Analyzed {result['videos_analyzed']} videos, "
                f"{result['videos_successful']} successful, "
                f"{result['videos_failed']} failed"
            )
            await broadcast_robot_status('robot3', 'idle', 'Analysis completed')

            logger.info(f"Metric Analyzer completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in Metric Analyzer: {e}", exc_info=True)

            # Update job status
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            self.db.commit()

            # Broadcast failure
            await broadcast_job_failed(self.job_id, 'robot3', str(e))
            await broadcast_robot_status('robot3', 'error', f"Analysis failed: {e}")

            return {
                "status": "failed",
                "error": str(e),
                "videos_analyzed": 0
            }

    async def _build_video_query(
        self,
        video_ids: Optional[List[int]],
        search_query_id: Optional[int],
        seed_topic_id: Optional[int],
        niche: Optional[str],
        batch_size: int,
        reanalyze: bool
    ) -> List[Video]:
        """
        Build video query with hybrid filters.

        Priority:
        1. video_ids (specific videos)
        2. search_query_id (videos from specific search)
        3. seed_topic_id (videos from specific topic via search_queries)
        4. niche (videos from specific niche via seed_topics)
        5. Default: all unanalyzed videos

        Args:
            video_ids: Specific video IDs
            search_query_id: Search query ID filter
            seed_topic_id: Seed topic ID filter
            niche: Niche name filter
            batch_size: Max results
            reanalyze: Include already analyzed videos

        Returns:
            List of Video objects
        """
        query = select(Video)

        # Apply filters (priority order)
        if video_ids:
            query = query.where(Video.id.in_(video_ids))
            logger.info(f"Filtering by specific video IDs: {video_ids}")

        elif search_query_id:
            query = query.where(Video.search_query_id == search_query_id)
            logger.info(f"Filtering by search_query_id: {search_query_id}")

        elif seed_topic_id:
            # Join through search_queries to filter by seed_topic_id
            query = query.join(SearchQuery).where(SearchQuery.seed_topic_id == seed_topic_id)
            logger.info(f"Filtering by seed_topic_id: {seed_topic_id}")

        elif niche:
            # Join through search_queries -> seed_topics to filter by niche
            query = query.join(SearchQuery).join(SeedTopic).where(SeedTopic.niche == niche)
            logger.info(f"Filtering by niche: {niche}")

        else:
            logger.info("No filters specified - processing all unanalyzed videos")

        # Filter by metrics_analyzed flag unless reanalyze=True
        if not reanalyze:
            query = query.where(Video.metrics_analyzed == False)

        # Apply batch size limit
        query = query.limit(batch_size)

        # Execute query
        result = self.db.execute(query)
        videos = result.scalars().all()

        return videos

    async def _initialize_clients(self):
        """Initialize YouTube Data API and Google Ads API clients."""
        logger.info("Initializing API clients")

        # Initialize YouTube Data API client
        youtube_enabled = self.config_manager.get('robot3.youtube_api_enabled', True, 'robot3')
        if youtube_enabled:
            try:
                from googleapiclient.discovery import build

                api_key = self.config_manager.get('youtube.api_key', None, 'api_keys')

                if api_key:
                    self.youtube_client = build('youtube', 'v3', developerKey=api_key)
                    logger.info("YouTube API client initialized")
                else:
                    logger.warning("YouTube API key not configured")
                    self.youtube_client = None
            except ImportError:
                logger.warning("google-api-python-client not installed")
                self.youtube_client = None
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API client: {e}")
                self.youtube_client = None
        else:
            logger.info("YouTube API disabled in configuration")

        # Initialize Google Ads API client
        google_ads_enabled = self.config_manager.get('robot3.google_ads_enabled', False, 'robot3')
        if google_ads_enabled:
            try:
                # TODO: Implement Google Ads API client initialization
                # Requires: developer_token, client_id, client_secret, refresh_token, customer_id
                logger.warning("Google Ads API integration not yet implemented")
                self.google_ads_client = None
            except Exception as e:
                logger.error(f"Failed to initialize Google Ads API client: {e}")
                self.google_ads_client = None
        else:
            logger.info("Google Ads API disabled in configuration")

        # Initialize service layer
        self.service = MetricAnalyzerService(
            youtube_client=self.youtube_client,
            google_ads_client=self.google_ads_client
        )

    async def _process_videos(self, videos: List[Video]) -> Dict:
        """
        Process videos and calculate metrics.

        Args:
            videos: List of Video objects to analyze

        Returns:
            Dict with processing results
        """
        total_videos = len(videos)
        videos_successful = 0
        videos_failed = 0
        videos_skipped = 0

        delay_between_videos = self.config_manager.get('robot3.delay_between_videos', 0.5, 'robot3')
        skip_on_api_error = self.config_manager.get('robot3.skip_on_api_error', True, 'robot3')

        # Get scoring weights from config
        weights = {
            'search_volume': self.config_manager.get('robot3.weight_search_volume', 25, 'robot3'),
            'competition': self.config_manager.get('robot3.weight_competition', 20, 'robot3'),
            'velocity': self.config_manager.get('robot3.weight_velocity', 20, 'robot3'),
            'engagement': self.config_manager.get('robot3.weight_engagement', 20, 'robot3'),
            'sentiment': self.config_manager.get('robot3.weight_sentiment', 0, 'robot3'),
            'recency': self.config_manager.get('robot3.weight_recency', 15, 'robot3')
        }

        logger.info(f"Using scoring weights: {weights}")

        for idx, video in enumerate(videos):
            try:
                # Update progress
                progress = int((idx / total_videos) * 100)
                await self._update_progress(
                    progress,
                    f"Analyzing video {idx + 1}/{total_videos}: {video.title[:50]}..."
                )

                # Analyze video
                success = await self._analyze_video(video, weights, skip_on_api_error)

                if success:
                    videos_successful += 1
                elif success is False:
                    videos_failed += 1
                else:
                    videos_skipped += 1

                # Rate limiting
                if idx < total_videos - 1:
                    await asyncio.sleep(delay_between_videos)

            except Exception as e:
                logger.error(f"Error processing video {video.id}: {e}", exc_info=True)
                videos_failed += 1

        return {
            "status": "completed",
            "videos_analyzed": total_videos,
            "videos_successful": videos_successful,
            "videos_failed": videos_failed,
            "videos_skipped": videos_skipped
        }

    async def _analyze_video(self, video: Video, weights: Dict, skip_on_api_error: bool) -> Optional[bool]:
        """
        Analyze a single video.

        Args:
            video: Video object to analyze
            weights: Scoring weights
            skip_on_api_error: Skip video if API error occurs

        Returns:
            True if successful, False if failed, None if skipped
        """
        logger.info(f"Analyzing video: {video.video_id} - {video.title}")

        try:
            # Step 1: Fetch YouTube metrics
            youtube_metrics = self.service.fetch_youtube_metrics(video.video_id)
            if not youtube_metrics and skip_on_api_error:
                logger.warning(f"Failed to fetch YouTube metrics for {video.video_id}, skipping")
                return None

            # Step 2: Fetch channel metrics
            channel_metrics = None
            if youtube_metrics and youtube_metrics.get('channel_id'):
                channel_metrics = self.service.fetch_channel_metrics(youtube_metrics['channel_id'])

            # Step 3: Calculate engagement metrics
            engagement_metrics = self.service.calculate_engagement_metrics(youtube_metrics or {})

            # Step 4: Calculate velocity metrics
            published_at = datetime.fromisoformat(youtube_metrics['published_at'].replace('Z', '+00:00')) \
                if youtube_metrics and youtube_metrics.get('published_at') else video.published_at
            velocity_metrics = self.service.calculate_velocity_metrics(
                youtube_metrics or {},
                published_at
            )

            # Step 5: Calculate subscriber view ratio
            subscriber_count = channel_metrics.get('subscriber_count', 0) if channel_metrics else 0
            subscriber_view_ratio = self.service.calculate_subscriber_view_ratio(
                youtube_metrics.get('view_count', 0) if youtube_metrics else 0,
                subscriber_count
            )

            # Step 6: Calculate virality score
            virality_score = self.service.calculate_virality_score(
                engagement_metrics['engagement_rate'],
                velocity_metrics['views_per_day'],
                subscriber_view_ratio
            )

            # Step 7: Fetch Google Ads metrics (optional)
            # Extract keywords from video title for search volume lookup
            keywords = [video.title] if video.title else []
            google_ads_metrics = self.service.fetch_google_ads_metrics(keywords)

            # Step 8: Save VideoMetric record
            video_metric = VideoMetric(
                video_id=video.id,
                # YouTube API metrics
                view_count=youtube_metrics.get('view_count') if youtube_metrics else None,
                like_count=youtube_metrics.get('like_count') if youtube_metrics else None,
                dislike_count=youtube_metrics.get('dislike_count') if youtube_metrics else None,
                comment_count=youtube_metrics.get('comment_count') if youtube_metrics else None,
                favorite_count=youtube_metrics.get('favorite_count') if youtube_metrics else None,
                # Engagement metrics
                engagement_rate=engagement_metrics['engagement_rate'],
                like_ratio=engagement_metrics['like_ratio'],
                comment_rate=engagement_metrics['comment_rate'],
                # Velocity metrics
                views_per_day=velocity_metrics['views_per_day'],
                recent_view_velocity=velocity_metrics['recent_view_velocity'],
                # Google Ads metrics
                keyword_search_volume=google_ads_metrics.get('avg_monthly_searches') if google_ads_metrics else None,
                keyword_competition=google_ads_metrics.get('competition') if google_ads_metrics else None,
                keyword_cpc=google_ads_metrics.get('avg_cpc_usd') if google_ads_metrics else None,
                # Sentiment (placeholder for now)
                sentiment_score=None,
                sentiment_magnitude=None,
                # Tags and category
                tags=json.dumps(youtube_metrics.get('tags', [])) if youtube_metrics else None,
                category_id=int(youtube_metrics.get('category_id')) if youtube_metrics and youtube_metrics.get('category_id') else None,
                # Advanced metrics
                subscriber_view_ratio=subscriber_view_ratio,
                virality_score=virality_score,
                # Raw data
                youtube_api_response=json.dumps(youtube_metrics.get('raw_response')) if youtube_metrics else None,
                google_ads_response=json.dumps(google_ads_metrics) if google_ads_metrics else None
            )

            # Step 9: Calculate component scores
            component_scores = {
                'search_volume': self.service.calculate_search_volume_score(
                    google_ads_metrics.get('avg_monthly_searches') if google_ads_metrics else None
                ),
                'competition': self.service.calculate_competition_score(
                    # TODO: Get actual competing video count from database
                    # For now, use placeholder based on search volume
                    50  # Placeholder
                ),
                'velocity': self.service.calculate_velocity_score(
                    velocity_metrics['views_per_day'],
                    subscriber_count
                ),
                'engagement': self.service.calculate_engagement_score(
                    engagement_metrics['engagement_rate']
                ),
                'sentiment': self.service.calculate_sentiment_score(None),  # Not implemented yet
                'recency': self.service.calculate_recency_score(published_at)
            }

            # Step 10: Calculate overall opportunity score
            overall_score = self.service.calculate_opportunity_score(component_scores, weights)

            # Step 11: Determine competition level
            competition_level_str = self.service.determine_competition_level(
                50,  # Placeholder competing_videos
                low_threshold=self.config_manager.get('robot3.competition_low_threshold', 10, 'robot3'),
                medium_threshold=self.config_manager.get('robot3.competition_medium_threshold', 50, 'robot3'),
                high_threshold=self.config_manager.get('robot3.competition_high_threshold', 200, 'robot3')
            )
            competition_level = CompetitionLevel[competition_level_str.upper()]

            # Step 12: Identify content gaps
            content_gap, recommended_angle = self.service.identify_content_gap(
                video.title,
                50,  # Placeholder competing_videos
                10000,  # Placeholder average_views
                google_ads_metrics.get('avg_monthly_searches') if google_ads_metrics else None
            )

            # Step 13: Predict trend
            trend_prediction, confidence_score = self.service.predict_trend(
                velocity_metrics['views_per_day'],
                velocity_metrics['days_since_publish'],
                component_scores['recency']
            )

            # Step 14: Determine if recommended
            min_opportunity_score = self.config_manager.get('robot3.min_opportunity_score', 70, 'robot3')
            is_recommended = 1 if overall_score >= min_opportunity_score else 0

            # Step 15: Save OpportunityScore record
            opportunity_score = OpportunityScore(
                video_id=video.id,
                overall_score=overall_score,
                # Component scores
                search_volume_score=component_scores['search_volume'],
                competition_score=component_scores['competition'],
                velocity_score=component_scores['velocity'],
                engagement_score=component_scores['engagement'],
                sentiment_score=component_scores['sentiment'],
                recency_score=component_scores['recency'],
                # Competition analysis
                competition_level=competition_level,
                total_competing_videos=50,  # Placeholder
                average_competitor_views=10000,  # Placeholder
                # Content gap
                content_gap_identified=content_gap,
                recommended_angle=recommended_angle,
                # Scoring weights
                weights=json.dumps(weights),
                # Trend prediction
                trend_prediction=trend_prediction,
                confidence_score=confidence_score,
                # Recommendation
                is_recommended=is_recommended
            )

            # Step 16: Update video flags
            video.metrics_analyzed = True
            if channel_metrics:
                video.subscriber_count = subscriber_count

            # Commit to database
            self.db.add(video_metric)
            self.db.add(opportunity_score)
            self.db.commit()

            logger.info(f"✓ Video analyzed: {video.video_id} - Score: {overall_score:.2f}")
            return True

        except Exception as e:
            logger.error(f"Error analyzing video {video.id}: {e}", exc_info=True)
            self.db.rollback()
            return False

    async def _update_progress(self, percentage: int, step: str):
        """Update job progress in database and broadcast via SSE."""
        if self.job_id:
            job = self.db.query(JobStatus).filter(JobStatus.id == self.job_id).first()
            if job:
                job.progress_percent = percentage
                job.current_step = step
                self.db.commit()

            await broadcast_job_progress(self.job_id, 'robot3', percentage, step)
