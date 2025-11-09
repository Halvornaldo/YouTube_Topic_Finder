"""Video metrics model - detailed metrics from Robot 3 (Metric Analyzer)."""

from sqlalchemy import Column, Integer, Float, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from src.models.base import Base, TimestampMixin


class VideoMetric(Base, TimestampMixin):
    """
    Detailed metrics analyzed by Robot 3.

    Includes data from YouTube Data API, Google Ads API,
    and calculated performance indicators.
    """

    __tablename__ = "video_metrics"

    # Foreign key
    video_id = Column(Integer, ForeignKey("videos.id"), unique=True, nullable=False, index=True)

    # YouTube API metrics
    view_count = Column(Integer, nullable=True)
    like_count = Column(Integer, nullable=True)
    dislike_count = Column(Integer, nullable=True)
    comment_count = Column(Integer, nullable=True)
    favorite_count = Column(Integer, nullable=True)

    # Engagement metrics (calculated)
    engagement_rate = Column(Float, nullable=True)  # (likes + comments) / views
    like_ratio = Column(Float, nullable=True)  # likes / (likes + dislikes)
    comment_rate = Column(Float, nullable=True)  # comments / views

    # View velocity (calculated)
    views_per_day = Column(Float, nullable=True)  # Average views per day since publish
    recent_view_velocity = Column(Float, nullable=True)  # Views in last 7 days / 7

    # Search volume (from Google Ads API)
    keyword_search_volume = Column(Integer, nullable=True)  # Monthly searches
    keyword_competition = Column(Float, nullable=True)  # 0-1 competition score
    keyword_cpc = Column(Float, nullable=True)  # Cost per click (USD)

    # Sentiment analysis
    sentiment_score = Column(Float, nullable=True)  # -1 (negative) to 1 (positive)
    sentiment_magnitude = Column(Float, nullable=True)  # 0-1 strength of sentiment

    # Tag analysis
    tags = Column(JSON, nullable=True)  # List of video tags
    category_id = Column(Integer, nullable=True)  # YouTube category ID

    # Advanced metrics
    subscriber_view_ratio = Column(Float, nullable=True)  # views / subscriber_count
    virality_score = Column(Float, nullable=True)  # Custom virality calculation

    # Raw data storage
    youtube_api_response = Column(JSON, nullable=True)
    google_ads_response = Column(JSON, nullable=True)

    # Notes
    analysis_notes = Column(Text, nullable=True)

    # Relationships
    video = relationship("Video", back_populates="metrics")

    def __repr__(self):
        return f"<VideoMetric(id={self.id}, video_id={self.video_id}, engagement_rate={self.engagement_rate})>"
