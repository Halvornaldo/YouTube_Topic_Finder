"""Video model - candidate videos discovered by Robot 2 (SERP Scraper)."""

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from src.models.base import Base, TimestampMixin


class Video(Base, TimestampMixin):
    """
    Candidate videos discovered by Robot 2.

    These are YouTube videos found through search results
    that will be analyzed for opportunity scoring.
    """

    __tablename__ = "videos"

    # YouTube identifiers
    video_id = Column(String(20), unique=True, nullable=False, index=True)  # YouTube video ID
    channel_id = Column(String(50), nullable=True, index=True)
    channel_name = Column(String(200), nullable=True)

    # Video metadata
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Basic metrics (from initial scrape)
    view_count = Column(Integer, nullable=True)
    like_count = Column(Integer, nullable=True)
    comment_count = Column(Integer, nullable=True)
    subscriber_count = Column(Integer, nullable=True)  # Channel subscribers

    # Search context
    search_query_id = Column(Integer, ForeignKey("search_queries.id"), nullable=True, index=True)
    search_rank = Column(Integer, nullable=True)  # Position in search results

    # Processing flags
    metrics_analyzed = Column(Boolean, default=False)  # Robot 3 completed
    format_classified = Column(Boolean, default=False)  # Robot 4 completed
    transcript_downloaded = Column(Boolean, default=False)

    # Relationships
    search_query = relationship("SearchQuery", back_populates="videos")
    metrics = relationship("VideoMetric", back_populates="video", uselist=False, cascade="all, delete-orphan")
    opportunity_score = relationship("OpportunityScore", back_populates="video", uselist=False, cascade="all, delete-orphan")
    video_format = relationship("VideoFormat", back_populates="video", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video(id={self.id}, video_id='{self.video_id}', title='{self.title[:50]}...')>"
