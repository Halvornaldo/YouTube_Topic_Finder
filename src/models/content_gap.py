"""Content gap model - identified market gaps and opportunities."""

from sqlalchemy import Column, String, Integer, Float, Text, JSON, Enum
from sqlalchemy.orm import relationship
import enum
from src.models.base import Base, TimestampMixin


class GapType(str, enum.Enum):
    """Type of content gap identified."""
    FORMAT_GAP = "format_gap"  # Missing format for a topic
    QUALITY_GAP = "quality_gap"  # Low quality content dominates
    DEPTH_GAP = "depth_gap"  # Superficial coverage only
    RECENCY_GAP = "recency_gap"  # Outdated content
    AUDIENCE_GAP = "audience_gap"  # Underserved audience segment


class ContentGap(Base, TimestampMixin):
    """
    Content gaps identified during analysis.

    These represent opportunities where search demand exists
    but quality content is lacking.
    """

    __tablename__ = "content_gaps"

    # Gap identification
    topic = Column(String(500), nullable=False, index=True)
    niche = Column(String(100), nullable=False, index=True)
    gap_type = Column(Enum(GapType), nullable=False, index=True)

    # Gap details
    description = Column(Text, nullable=False)
    recommended_approach = Column(Text, nullable=True)

    # Opportunity metrics
    search_volume = Column(Integer, nullable=True)
    current_competition = Column(Integer, nullable=True)  # Number of videos
    opportunity_score = Column(Float, nullable=True)  # 0-100

    # Missing elements
    missing_formats = Column(JSON, nullable=True)  # List of format types
    missing_angles = Column(JSON, nullable=True)  # List of content angles

    # Target audience
    target_audience = Column(String(200), nullable=True)
    audience_size = Column(Integer, nullable=True)

    # Supporting data
    related_topics = Column(JSON, nullable=True)
    keywords = Column(JSON, nullable=True)

    # Status
    validated = Column(Integer, default=0)  # Boolean - manually validated
    exploited = Column(Integer, default=0)  # Boolean - content created

    def __repr__(self):
        return f"<ContentGap(id={self.id}, topic='{self.topic}', type={self.gap_type})>"
