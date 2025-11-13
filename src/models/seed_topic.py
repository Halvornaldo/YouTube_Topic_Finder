"""Seed topics model - topics discovered by Robot 1 (Horizon Scanner)."""

from sqlalchemy import Column, String, Float, Integer, Text, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from src.models.base import Base, TimestampMixin


class SourceType(str, enum.Enum):
    """Source where the topic was discovered."""
    GOOGLE_TRENDS = "google_trends"
    REDDIT = "reddit"
    GDELT = "gdelt"
    MANUAL = "manual"


class TrendStatus(str, enum.Enum):
    """Status of the trend."""
    RISING = "rising"
    PEAK = "peak"
    DECLINING = "declining"
    STABLE = "stable"


class SeedTopic(Base, TimestampMixin):
    """
    Seed topics discovered by Robot 1.

    These are trending topics identified from Google Trends and Reddit
    that will be used to search for YouTube videos.
    """

    __tablename__ = "seed_topics"

    # Core fields
    topic = Column(String(500), nullable=False, index=True)
    source = Column(Enum(SourceType), nullable=False, index=True)
    niche = Column(String(100), nullable=False, index=True)

    # Trend metrics
    trend_score = Column(Float, nullable=True)  # 0-100 score from Google Trends
    search_volume = Column(Integer, nullable=True)  # Estimated search volume
    trend_status = Column(Enum(TrendStatus), default=TrendStatus.RISING)

    # Source-specific data
    source_url = Column(Text, nullable=True)  # URL where topic was found
    source_metadata = Column(JSON, nullable=True)  # Additional metadata (subreddit, upvotes, etc.)

    # Related keywords
    keywords = Column(JSON, nullable=True)  # List of related keywords

    # Processing status
    processed = Column(Integer, default=0)  # 0=new, 1=scraped, 2=analyzed, 3=completed

    # Relationships
    search_queries = relationship("SearchQuery", back_populates="seed_topic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SeedTopic(id={self.id}, topic='{self.topic}', source={self.source}, niche='{self.niche}')>"
