"""Search query model - tracks YouTube searches performed."""

from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from src.models.base import Base, TimestampMixin


class SearchQuery(Base, TimestampMixin):
    """
    Search queries performed against YouTube.

    Tracks all searches done by Robot 2 to find candidate videos.
    """

    __tablename__ = "search_queries"

    # Query details
    query_text = Column(String(500), nullable=False, index=True)
    seed_topic_id = Column(Integer, ForeignKey("seed_topics.id"), nullable=True, index=True)
    niche = Column(String(100), nullable=True, index=True)

    # Search parameters
    max_results = Column(Integer, default=50)
    region_code = Column(String(5), nullable=True)  # e.g., "US"
    language_code = Column(String(5), nullable=True)  # e.g., "en"

    # Results metadata
    total_results = Column(Integer, nullable=True)  # Total results found
    videos_scraped = Column(Integer, default=0)  # Number of videos saved
    search_method = Column(String(50), nullable=True)  # "playwright" or "api"

    # Performance tracking
    execution_time_seconds = Column(Integer, nullable=True)
    success = Column(Integer, default=1)  # Boolean
    error_message = Column(Text, nullable=True)

    # Raw response (for debugging)
    raw_response = Column(JSON, nullable=True)

    # Relationships
    seed_topic = relationship("SeedTopic", back_populates="search_queries")
    videos = relationship("Video", back_populates="search_query", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SearchQuery(id={self.id}, query='{self.query_text}', videos={self.videos_scraped})>"
