"""Service layer for SERP Scraper operations."""

import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc
from datetime import datetime, timedelta

from src.models.video import Video
from src.models.search_query import SearchQuery
from src.models.seed_topic import SeedTopic

logger = logging.getLogger(__name__)


class SerpScraperService:
    """
    Service layer for Robot 2 (SERP Scraper) operations.

    Provides CRUD operations, statistics, and business logic
    for videos and search queries.
    """

    def __init__(self, db_session: Session):
        """
        Initialize service.

        Args:
            db_session: Database session
        """
        self.db = db_session

    # Video CRUD operations

    def get_video_by_id(self, video_id: int) -> Optional[Video]:
        """Get video by database ID."""
        return self.db.query(Video).filter(Video.id == video_id).first()

    def get_video_by_youtube_id(self, youtube_id: str) -> Optional[Video]:
        """Get video by YouTube video ID."""
        return self.db.query(Video).filter(Video.video_id == youtube_id).first()

    def get_videos(
        self,
        niche: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        metrics_analyzed: Optional[bool] = None,
        format_classified: Optional[bool] = None,
        order_by: str = 'created_at'
    ) -> List[Video]:
        """
        Get videos with optional filtering.

        Args:
            niche: Filter by niche name
            limit: Maximum number of results
            offset: Offset for pagination
            metrics_analyzed: Filter by Robot 3 processing status
            format_classified: Filter by Robot 4 processing status
            order_by: Sort field (created_at, view_count, published_at)

        Returns:
            List of videos
        """
        query = self.db.query(Video)

        # Apply filters
        if niche:
            query = query.join(SearchQuery).join(SeedTopic).filter(
                SeedTopic.niche == niche
            )

        if metrics_analyzed is not None:
            query = query.filter(Video.metrics_analyzed == metrics_analyzed)

        if format_classified is not None:
            query = query.filter(Video.format_classified == format_classified)

        # Apply ordering
        if order_by == 'view_count':
            query = query.order_by(desc(Video.view_count))
        elif order_by == 'published_at':
            query = query.order_by(desc(Video.published_at))
        else:  # Default: created_at
            query = query.order_by(desc(Video.created_at))

        return query.offset(offset).limit(limit).all()

    def get_videos_for_analysis(self, limit: int = 100) -> List[Video]:
        """
        Get videos ready for Robot 3 analysis (metrics_analyzed = False).

        Args:
            limit: Maximum number of videos

        Returns:
            List of unanalyzed videos
        """
        return self.db.query(Video).filter(
            Video.metrics_analyzed == False
        ).order_by(Video.created_at.desc()).limit(limit).all()

    def get_videos_for_classification(self, limit: int = 100) -> List[Video]:
        """
        Get videos ready for Robot 4 classification (format_classified = False).

        Args:
            limit: Maximum number of videos

        Returns:
            List of unclassified videos
        """
        return self.db.query(Video).filter(
            and_(
                Video.metrics_analyzed == True,  # Must be analyzed first
                Video.format_classified == False
            )
        ).order_by(Video.created_at.desc()).limit(limit).all()

    def mark_video_analyzed(self, video_id: int) -> bool:
        """
        Mark video as analyzed by Robot 3.

        Args:
            video_id: Database ID of video

        Returns:
            True if successful
        """
        video = self.get_video_by_id(video_id)
        if not video:
            return False

        video.metrics_analyzed = True
        video.updated_at = datetime.utcnow()

        try:
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking video as analyzed: {e}")
            self.db.rollback()
            return False

    def mark_video_classified(self, video_id: int) -> bool:
        """
        Mark video as classified by Robot 4.

        Args:
            video_id: Database ID of video

        Returns:
            True if successful
        """
        video = self.get_video_by_id(video_id)
        if not video:
            return False

        video.format_classified = True
        video.updated_at = datetime.utcnow()

        try:
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking video as classified: {e}")
            self.db.rollback()
            return False

    def delete_video(self, video_id: int) -> bool:
        """
        Delete a video.

        Args:
            video_id: Database ID of video

        Returns:
            True if successful
        """
        video = self.get_video_by_id(video_id)
        if not video:
            return False

        try:
            self.db.delete(video)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting video: {e}")
            self.db.rollback()
            return False

    # Search Query operations

    def get_search_query(self, query_id: int) -> Optional[SearchQuery]:
        """Get search query by ID."""
        return self.db.query(SearchQuery).filter(SearchQuery.id == query_id).first()

    def get_search_queries(
        self,
        niche: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SearchQuery]:
        """
        Get search queries with optional filtering.

        Args:
            niche: Filter by niche
            success: Filter by success status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of search queries
        """
        query = self.db.query(SearchQuery)

        if niche:
            query = query.filter(SearchQuery.niche == niche)

        if success is not None:
            query = query.filter(SearchQuery.success == (1 if success else 0))

        return query.order_by(desc(SearchQuery.created_at)).offset(offset).limit(limit).all()

    def get_failed_searches(self, limit: int = 50) -> List[SearchQuery]:
        """
        Get failed search queries for debugging.

        Args:
            limit: Maximum number of results

        Returns:
            List of failed searches
        """
        return self.db.query(SearchQuery).filter(
            SearchQuery.success == 0
        ).order_by(desc(SearchQuery.created_at)).limit(limit).all()

    # Statistics and reporting

    def get_video_stats(self, niche: Optional[str] = None) -> Dict:
        """
        Get video statistics.

        Args:
            niche: Optional niche filter

        Returns:
            Dict with statistics
        """
        query = self.db.query(Video)

        if niche:
            query = query.join(SearchQuery).join(SeedTopic).filter(
                SeedTopic.niche == niche
            )

        total_videos = query.count()
        analyzed = query.filter(Video.metrics_analyzed == True).count()
        classified = query.filter(Video.format_classified == True).count()
        pending_analysis = query.filter(Video.metrics_analyzed == False).count()
        pending_classification = query.filter(
            and_(
                Video.metrics_analyzed == True,
                Video.format_classified == False
            )
        ).count()

        return {
            'total_videos': total_videos,
            'analyzed': analyzed,
            'classified': classified,
            'pending_analysis': pending_analysis,
            'pending_classification': pending_classification,
            'analysis_percent': int((analyzed / total_videos * 100)) if total_videos > 0 else 0,
            'classification_percent': int((classified / total_videos * 100)) if total_videos > 0 else 0
        }

    def get_search_stats(self, niche: Optional[str] = None) -> Dict:
        """
        Get search query statistics.

        Args:
            niche: Optional niche filter

        Returns:
            Dict with statistics
        """
        query = self.db.query(SearchQuery)

        if niche:
            query = query.filter(SearchQuery.niche == niche)

        total_searches = query.count()
        successful = query.filter(SearchQuery.success == 1).count()
        failed = query.filter(SearchQuery.success == 0).count()

        # Count by method
        playwright_count = query.filter(SearchQuery.search_method == 'playwright').count()
        api_count = query.filter(SearchQuery.search_method == 'api').count()

        # Average execution time
        avg_time = self.db.query(func.avg(SearchQuery.execution_time_seconds)).filter(
            SearchQuery.success == 1
        ).scalar()

        # Total videos scraped
        total_videos_scraped = self.db.query(func.sum(SearchQuery.videos_scraped)).scalar() or 0

        return {
            'total_searches': total_searches,
            'successful': successful,
            'failed': failed,
            'success_rate': int((successful / total_searches * 100)) if total_searches > 0 else 0,
            'playwright_searches': playwright_count,
            'api_searches': api_count,
            'avg_execution_time_seconds': int(avg_time) if avg_time else 0,
            'total_videos_scraped': int(total_videos_scraped)
        }

    def get_top_channels(self, limit: int = 10, niche: Optional[str] = None) -> List[Dict]:
        """
        Get top channels by video count.

        Args:
            limit: Maximum number of channels
            niche: Optional niche filter

        Returns:
            List of dicts with channel info
        """
        query = self.db.query(
            Video.channel_name,
            Video.channel_id,
            func.count(Video.id).label('video_count'),
            func.avg(Video.view_count).label('avg_views')
        ).filter(
            Video.channel_name.isnot(None)
        )

        if niche:
            query = query.join(SearchQuery).join(SeedTopic).filter(
                SeedTopic.niche == niche
            )

        results = query.group_by(
            Video.channel_name,
            Video.channel_id
        ).order_by(
            desc('video_count')
        ).limit(limit).all()

        return [
            {
                'channel_name': r[0],
                'channel_id': r[1],
                'video_count': r[2],
                'avg_views': int(r[3]) if r[3] else 0
            }
            for r in results
        ]

    def get_recent_videos(self, limit: int = 20, niche: Optional[str] = None) -> List[Video]:
        """
        Get most recently discovered videos.

        Args:
            limit: Maximum number of videos
            niche: Optional niche filter

        Returns:
            List of videos
        """
        query = self.db.query(Video)

        if niche:
            query = query.join(SearchQuery).join(SeedTopic).filter(
                SeedTopic.niche == niche
            )

        return query.order_by(desc(Video.created_at)).limit(limit).all()

    def get_processing_queue_status(self) -> Dict:
        """
        Get status of processing queues for robots 3 and 4.

        Returns:
            Dict with queue statistics
        """
        # Videos waiting for Robot 3
        waiting_for_analysis = self.db.query(Video).filter(
            Video.metrics_analyzed == False
        ).count()

        # Videos waiting for Robot 4
        waiting_for_classification = self.db.query(Video).filter(
            and_(
                Video.metrics_analyzed == True,
                Video.format_classified == False
            )
        ).count()

        # Fully processed
        fully_processed = self.db.query(Video).filter(
            and_(
                Video.metrics_analyzed == True,
                Video.format_classified == True
            )
        ).count()

        total_videos = self.db.query(Video).count()

        return {
            'total_videos': total_videos,
            'waiting_for_robot3': waiting_for_analysis,
            'waiting_for_robot4': waiting_for_classification,
            'fully_processed': fully_processed,
            'processing_complete_percent': int((fully_processed / total_videos * 100)) if total_videos > 0 else 0
        }

    # Deduplication

    def find_duplicate_videos(self) -> List[Dict]:
        """
        Find duplicate videos (same YouTube video_id).

        Returns:
            List of dicts with duplicate info
        """
        duplicates = self.db.query(
            Video.video_id,
            func.count(Video.id).label('count')
        ).group_by(
            Video.video_id
        ).having(
            func.count(Video.id) > 1
        ).all()

        return [
            {
                'video_id': dup[0],
                'duplicate_count': dup[1]
            }
            for dup in duplicates
        ]

    def remove_duplicate_videos(self, keep_oldest: bool = True) -> int:
        """
        Remove duplicate videos, keeping only one.

        Args:
            keep_oldest: If True, keep oldest record; otherwise keep newest

        Returns:
            Number of duplicates removed
        """
        duplicates = self.find_duplicate_videos()
        removed_count = 0

        for dup in duplicates:
            video_id = dup['video_id']

            # Get all records with this video_id
            videos = self.db.query(Video).filter(
                Video.video_id == video_id
            ).order_by(
                Video.created_at.asc() if keep_oldest else Video.created_at.desc()
            ).all()

            # Keep first, delete rest
            for video in videos[1:]:
                try:
                    self.db.delete(video)
                    removed_count += 1
                except Exception as e:
                    logger.error(f"Error removing duplicate video {video.id}: {e}")
                    continue

        try:
            self.db.commit()
            logger.info(f"Removed {removed_count} duplicate videos")
        except Exception as e:
            logger.error(f"Error committing duplicate removal: {e}")
            self.db.rollback()
            removed_count = 0

        return removed_count
