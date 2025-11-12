"""Metric Analyzer Service - Business logic for Robot 3."""

import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)


class MetricAnalyzerService:
    """
    Service layer for Robot 3: Metric Analyzer.

    Handles:
    - YouTube Data API metric fetching
    - Google Ads API search volume lookup
    - Engagement metric calculations
    - Velocity metric calculations
    - Component score calculations (0-100 scale)
    - Opportunity score calculation (weighted average)
    - Competition level determination
    - Content gap analysis
    - Trend prediction
    """

    def __init__(self, youtube_client=None, google_ads_client=None):
        """
        Initialize the service with API clients.

        Args:
            youtube_client: Initialized YouTube Data API v3 client
            google_ads_client: Initialized Google Ads API client (optional)
        """
        self.youtube_client = youtube_client
        self.google_ads_client = google_ads_client

    # ========== YouTube API Methods ==========

    def fetch_youtube_metrics(self, video_id: str) -> Optional[Dict]:
        """
        Fetch video metrics from YouTube Data API v3.

        Args:
            video_id: YouTube video ID (e.g., "dQw4w9WgXcQ")

        Returns:
            Dict with video statistics and metadata, or None if failed

        Example return:
        {
            'view_count': 123456,
            'like_count': 5432,
            'comment_count': 987,
            'published_at': '2023-01-15T10:30:00Z',
            'channel_id': 'UCxxxxxx',
            'tags': ['ai', 'tutorial'],
            'category_id': '28',
            'duration': 'PT15M30S'  # ISO 8601 duration
        }
        """
        if not self.youtube_client:
            logger.warning("YouTube API client not initialized")
            return None

        try:
            # Request video details
            response = self.youtube_client.videos().list(
                part='statistics,snippet,contentDetails',
                id=video_id
            ).execute()

            if not response.get('items'):
                logger.warning(f"No data found for video ID: {video_id}")
                return None

            item = response['items'][0]
            statistics = item.get('statistics', {})
            snippet = item.get('snippet', {})
            content_details = item.get('contentDetails', {})

            # Parse data
            metrics = {
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'dislike_count': int(statistics.get('dislikeCount', 0)),  # Often unavailable
                'comment_count': int(statistics.get('commentCount', 0)),
                'favorite_count': int(statistics.get('favoriteCount', 0)),
                'published_at': snippet.get('publishedAt'),
                'channel_id': snippet.get('channelId'),
                'tags': snippet.get('tags', []),
                'category_id': snippet.get('categoryId'),
                'duration': content_details.get('duration'),  # ISO 8601 format
                'raw_response': item  # Store full response for debugging
            }

            logger.info(f"Fetched metrics for video {video_id}: {metrics['view_count']} views")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching YouTube metrics for {video_id}: {e}")
            return None

    def fetch_channel_metrics(self, channel_id: str) -> Optional[Dict]:
        """
        Fetch channel metrics from YouTube Data API v3.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Dict with channel statistics, or None if failed

        Example return:
        {
            'subscriber_count': 100000,
            'view_count': 5000000,
            'video_count': 250
        }
        """
        if not self.youtube_client:
            logger.warning("YouTube API client not initialized")
            return None

        try:
            response = self.youtube_client.channels().list(
                part='statistics',
                id=channel_id
            ).execute()

            if not response.get('items'):
                logger.warning(f"No data found for channel ID: {channel_id}")
                return None

            statistics = response['items'][0].get('statistics', {})

            metrics = {
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'view_count': int(statistics.get('viewCount', 0)),
                'video_count': int(statistics.get('videoCount', 0))
            }

            logger.info(f"Fetched channel metrics for {channel_id}: {metrics['subscriber_count']} subscribers")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching channel metrics for {channel_id}: {e}")
            return None

    # ========== Google Ads API Methods ==========

    def fetch_google_ads_metrics(self, keywords: List[str]) -> Optional[Dict]:
        """
        Fetch search volume and competition data from Google Ads API.

        Args:
            keywords: List of keywords to look up (e.g., ['ai tutorial', 'machine learning'])

        Returns:
            Dict with aggregated search volume metrics, or None if failed

        Example return:
        {
            'avg_monthly_searches': 12000,
            'competition': 0.65,  # 0-1 scale (LOW=0-0.33, MEDIUM=0.34-0.66, HIGH=0.67-1.0)
            'competition_level': 'MEDIUM',
            'avg_cpc_usd': 1.25
        }
        """
        if not self.google_ads_client:
            logger.warning("Google Ads API client not initialized - skipping search volume")
            return None

        try:
            # TODO: Implement Google Ads API call
            # This requires proper authentication and customer ID
            # For now, return placeholder
            logger.warning("Google Ads API integration not yet implemented")
            return None

        except Exception as e:
            logger.error(f"Error fetching Google Ads metrics: {e}")
            return None

    # ========== Engagement Metrics ==========

    def calculate_engagement_metrics(self, video_data: Dict) -> Dict:
        """
        Calculate engagement metrics from video statistics.

        Args:
            video_data: Dict with view_count, like_count, comment_count

        Returns:
            Dict with calculated engagement metrics

        Example return:
        {
            'engagement_rate': 0.0542,  # (likes + comments) / views
            'like_ratio': 0.98,  # likes / (likes + dislikes)
            'comment_rate': 0.0123  # comments / views
        }
        """
        view_count = video_data.get('view_count', 0)
        like_count = video_data.get('like_count', 0)
        dislike_count = video_data.get('dislike_count', 0)
        comment_count = video_data.get('comment_count', 0)

        # Avoid division by zero
        engagement_rate = 0.0
        like_ratio = 0.0
        comment_rate = 0.0

        if view_count > 0:
            engagement_rate = (like_count + comment_count) / view_count
            comment_rate = comment_count / view_count

        if (like_count + dislike_count) > 0:
            like_ratio = like_count / (like_count + dislike_count)

        return {
            'engagement_rate': round(engagement_rate, 6),
            'like_ratio': round(like_ratio, 4),
            'comment_rate': round(comment_rate, 6)
        }

    # ========== Velocity Metrics ==========

    def calculate_velocity_metrics(self, video_data: Dict, published_at: datetime) -> Dict:
        """
        Calculate view velocity metrics.

        Args:
            video_data: Dict with view_count
            published_at: Video publish datetime

        Returns:
            Dict with velocity metrics

        Example return:
        {
            'views_per_day': 1234.5,
            'recent_view_velocity': None,  # Requires historical data (not available yet)
            'days_since_publish': 45
        }
        """
        view_count = video_data.get('view_count', 0)
        now = datetime.now(tz=published_at.tzinfo)
        days_since_publish = max((now - published_at).days, 1)  # At least 1 day

        views_per_day = view_count / days_since_publish

        # Note: recent_view_velocity requires historical view data
        # For now, we'll set it to None (can be implemented later with caching)
        recent_view_velocity = None

        return {
            'views_per_day': round(views_per_day, 2),
            'recent_view_velocity': recent_view_velocity,
            'days_since_publish': days_since_publish
        }

    def calculate_subscriber_view_ratio(self, view_count: int, subscriber_count: int) -> float:
        """
        Calculate the ratio of views to subscriber count.

        Args:
            view_count: Video views
            subscriber_count: Channel subscribers

        Returns:
            Views per subscriber ratio
        """
        if subscriber_count == 0:
            return 0.0

        return round(view_count / subscriber_count, 4)

    def calculate_virality_score(self, engagement_rate: float, views_per_day: float,
                                 subscriber_view_ratio: float) -> float:
        """
        Calculate a custom virality score.

        Formula: Weighted combination of engagement, velocity, and subscriber ratio

        Args:
            engagement_rate: Engagement rate (0-1)
            views_per_day: Average views per day
            subscriber_view_ratio: Views / subscribers

        Returns:
            Virality score (0-100)
        """
        # Normalize views_per_day (log scale)
        normalized_velocity = min(100, math.log10(views_per_day + 1) * 10)

        # Normalize engagement rate (scale up)
        normalized_engagement = min(100, engagement_rate * 10000)

        # Normalize subscriber ratio
        normalized_ratio = min(100, subscriber_view_ratio * 100)

        # Weighted average (velocity=40%, engagement=40%, ratio=20%)
        virality = (
            normalized_velocity * 0.4 +
            normalized_engagement * 0.4 +
            normalized_ratio * 0.2
        )

        return round(virality, 2)

    # ========== Component Scores (0-100) ==========

    def calculate_search_volume_score(self, search_volume: Optional[int]) -> float:
        """
        Calculate search volume score (0-100).

        Uses logarithmic scale for 0-10M monthly searches.

        Args:
            search_volume: Monthly search volume

        Returns:
            Score 0-100
        """
        if search_volume is None or search_volume <= 0:
            return 50.0  # Neutral score if data unavailable

        # Logarithmic scale: 0-10M searches
        # 1K = ~30, 10K = ~40, 100K = ~50, 1M = ~60, 10M = ~70
        score = min(100, (math.log10(search_volume + 1) / 7) * 100)
        return round(score, 2)

    def calculate_competition_score(self, competing_videos: int) -> float:
        """
        Calculate competition score (0-100).

        INVERTED: Fewer competing videos = higher score.

        Args:
            competing_videos: Number of competing videos

        Returns:
            Score 0-100
        """
        # Inverse relationship: fewer videos = higher score
        # 0-10 videos = 90-100, 10-50 = 70-90, 50-200 = 30-70, 200+ = 0-30
        if competing_videos <= 10:
            score = 100 - competing_videos
        elif competing_videos <= 50:
            score = 90 - ((competing_videos - 10) / 40 * 20)
        elif competing_videos <= 200:
            score = 70 - ((competing_videos - 50) / 150 * 40)
        else:
            score = max(0, 30 - ((competing_videos - 200) / 100 * 30))

        return round(score, 2)

    def calculate_velocity_score(self, views_per_day: float, subscriber_count: int) -> float:
        """
        Calculate velocity score (0-100).

        Based on views_per_day relative to channel size.

        Args:
            views_per_day: Average views per day
            subscriber_count: Channel subscribers

        Returns:
            Score 0-100
        """
        # Normalize by channel size (views per 1K subscribers)
        if subscriber_count > 0:
            normalized = views_per_day / (subscriber_count / 1000)
        else:
            normalized = views_per_day / 10  # Default normalization

        # Scale to 0-100
        score = min(100, normalized * 10)
        return round(score, 2)

    def calculate_engagement_score(self, engagement_rate: float) -> float:
        """
        Calculate engagement score (0-100).

        Based on engagement rate (likes + comments) / views.

        Args:
            engagement_rate: Engagement rate (0-1)

        Returns:
            Score 0-100
        """
        # Scale up engagement rate (typically 0.01-0.10)
        # 1% = 10, 5% = 50, 10% = 100
        score = min(100, engagement_rate * 1000)
        return round(score, 2)

    def calculate_sentiment_score(self, sentiment: Optional[float]) -> float:
        """
        Calculate sentiment score (0-100).

        Based on comment sentiment analysis (-1 to 1).
        Currently returns neutral score as sentiment analysis is not implemented.

        Args:
            sentiment: Sentiment score -1 (negative) to 1 (positive)

        Returns:
            Score 0-100
        """
        if sentiment is None:
            return 50.0  # Neutral score

        # Convert -1 to 1 range into 0-100
        # -1 = 0, 0 = 50, 1 = 100
        score = (sentiment + 1) * 50
        return round(score, 2)

    def calculate_recency_score(self, published_at: datetime) -> float:
        """
        Calculate recency score (0-100).

        Based on how recent the video is (decay over 365 days).

        Args:
            published_at: Video publish datetime

        Returns:
            Score 0-100
        """
        now = datetime.now(tz=published_at.tzinfo)
        days_old = (now - published_at).days

        # Linear decay over 365 days
        # 0 days = 100, 180 days = 50, 365 days = 0
        score = max(0, 100 - (days_old / 365 * 100))
        return round(score, 2)

    # ========== Overall Opportunity Score ==========

    def calculate_opportunity_score(self, component_scores: Dict, weights: Dict) -> float:
        """
        Calculate overall opportunity score as weighted average.

        Args:
            component_scores: Dict with all 6 component scores (0-100)
            weights: Dict with weights for each component (must sum to 100)

        Example:
            component_scores = {
                'search_volume': 75.0,
                'competition': 80.0,
                'velocity': 65.0,
                'engagement': 70.0,
                'sentiment': 50.0,
                'recency': 90.0
            }
            weights = {
                'search_volume': 25,
                'competition': 20,
                'velocity': 20,
                'engagement': 20,
                'sentiment': 0,
                'recency': 15
            }

        Returns:
            Overall score 0-100
        """
        # Validate weights sum to 100
        total_weight = sum(weights.values())
        if abs(total_weight - 100) > 0.01:
            logger.warning(f"Weights sum to {total_weight}, expected 100. Normalizing...")
            # Normalize weights
            weights = {k: v / total_weight * 100 for k, v in weights.items()}

        # Calculate weighted average
        overall = sum(
            component_scores.get(component, 50.0) * (weights.get(component, 0) / 100)
            for component in weights.keys()
        )

        return round(overall, 2)

    # ========== Competition Analysis ==========

    def determine_competition_level(self, competing_videos: int,
                                    low_threshold: int = 10,
                                    medium_threshold: int = 50,
                                    high_threshold: int = 200) -> str:
        """
        Determine competition level based on number of competing videos.

        Args:
            competing_videos: Number of competing videos
            low_threshold: Max videos for LOW competition
            medium_threshold: Max videos for MEDIUM competition
            high_threshold: Max videos for HIGH competition

        Returns:
            Competition level: 'low', 'medium', 'high', or 'very_high'
        """
        if competing_videos <= low_threshold:
            return 'low'
        elif competing_videos <= medium_threshold:
            return 'medium'
        elif competing_videos <= high_threshold:
            return 'high'
        else:
            return 'very_high'

    # ========== Content Gap Analysis ==========

    def identify_content_gap(self, video_title: str, competing_videos: int,
                            average_views: int, search_volume: Optional[int]) -> Tuple[Optional[str], Optional[str]]:
        """
        Identify content gaps and recommend angles.

        This is a simple heuristic-based implementation.
        Can be enhanced with NLP and competitor analysis.

        Args:
            video_title: Video title
            competing_videos: Number of competing videos
            average_views: Average views of competitors
            search_volume: Monthly search volume

        Returns:
            Tuple of (content_gap_description, recommended_angle)
        """
        content_gap = None
        recommended_angle = None

        # High search volume + low competition = opportunity
        if search_volume and search_volume > 10000 and competing_videos < 20:
            content_gap = f"High search demand ({search_volume:,} monthly searches) with limited content"
            recommended_angle = "First-mover advantage - create comprehensive guide"

        # Medium competition but low average views = quality gap
        elif competing_videos > 20 and competing_videos < 100 and average_views < 10000:
            content_gap = "Existing content underperforming - quality opportunity"
            recommended_angle = "Create higher-quality version with better production value"

        # High competition but opportunity for unique angle
        elif competing_videos > 100:
            content_gap = "Saturated market - differentiation required"
            recommended_angle = "Find unique angle: beginner-friendly, advanced tips, specific use case"

        return content_gap, recommended_angle

    # ========== Trend Prediction ==========

    def predict_trend(self, views_per_day: float, days_since_publish: int,
                     recency_score: float) -> Tuple[str, float]:
        """
        Predict trend direction based on metrics.

        This is a simple heuristic. Can be enhanced with ML models.

        Args:
            views_per_day: Average views per day
            days_since_publish: Days since video was published
            recency_score: Recency score (0-100)

        Returns:
            Tuple of (trend_prediction, confidence_score)
            trend_prediction: 'rising', 'stable', or 'declining'
            confidence_score: 0-1 confidence in prediction
        """
        trend = 'stable'
        confidence = 0.5

        # Rising: Recent video with high daily views
        if days_since_publish < 30 and views_per_day > 1000:
            trend = 'rising'
            confidence = 0.8

        # Rising: High recency score with good velocity
        elif recency_score > 70 and views_per_day > 500:
            trend = 'rising'
            confidence = 0.7

        # Declining: Old video with low velocity
        elif days_since_publish > 180 and views_per_day < 100:
            trend = 'declining'
            confidence = 0.7

        # Declining: Low recency score
        elif recency_score < 30:
            trend = 'declining'
            confidence = 0.6

        # Stable: Everything else
        else:
            trend = 'stable'
            confidence = 0.6

        return trend, round(confidence, 2)
