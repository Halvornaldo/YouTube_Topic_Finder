"""Seed topics model - topics discovered by Robot 1 (Horizon Scanner)."""

from sqlalchemy import Column, String, Float, Integer, Text, Enum, JSON, DateTime
from sqlalchemy.orm import relationship
import enum
from src.models.base import Base, TimestampMixin


class SourceType(str, enum.Enum):
    """Source where the topic was discovered."""
    GOOGLE_TRENDS = "GOOGLE_TRENDS"
    REDDIT = "REDDIT"
    GDELT = "GDELT"
    MANUAL = "MANUAL"


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
    source = Column(Enum(SourceType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
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
    status = Column(String(20), server_default='pending')  # pending, scored, rejected (Robot 1.5)

    # Robot 1.5 (Topic Scorer) fields - LLM-based monetization scoring
    raw_score = Column(Float, nullable=True)  # Original engagement score (0-100)
    llm_score = Column(Float, nullable=True)  # LLM monetization score (0-100)
    final_score = Column(Float, nullable=True)  # Weighted combination of raw + LLM
    llm_reasoning = Column(Text, nullable=True)  # LLM explanation for the score
    profit_angle = Column(Text, nullable=True)  # Monetization strategy from LLM
    scored_at = Column(DateTime, nullable=True)  # When LLM scoring was performed
    llm_provider = Column(String(50), nullable=True)  # Which LLM was used (e.g., 'gemini-2.0-flash')

    # Relationships
    search_queries = relationship("SearchQuery", back_populates="seed_topic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SeedTopic(id={self.id}, topic='{self.topic}', source={self.source}, niche='{self.niche}')>"
