"""Opportunity score model - calculated opportunity scores from Robot 3."""

from sqlalchemy import Column, Integer, Float, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
import enum
from src.models.base import Base, TimestampMixin


class CompetitionLevel(str, enum.Enum):
    """Competition level for the topic."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class OpportunityScore(Base, TimestampMixin):
    """
    Calculated opportunity scores from Robot 3.

    Multi-factor analysis combining search volume, competition,
    view velocity, and sentiment to determine content opportunities.
    """

    __tablename__ = "opportunity_scores"

    # Foreign key
    video_id = Column(Integer, ForeignKey("videos.id"), unique=True, nullable=False, index=True)

    # Overall score (0-100)
    overall_score = Column(Float, nullable=False, index=True)

    # Component scores (0-100 each)
    search_volume_score = Column(Float, nullable=True)  # Based on keyword search volume
    competition_score = Column(Float, nullable=True)  # Based on number of competitors
    velocity_score = Column(Float, nullable=True)  # Based on view growth rate
    engagement_score = Column(Float, nullable=True)  # Based on engagement metrics
    sentiment_score = Column(Float, nullable=True)  # Based on comment sentiment
    recency_score = Column(Float, nullable=True)  # Based on how recent the video is

    # Competition analysis
    competition_level = Column(Enum(CompetitionLevel), nullable=True, index=True)
    total_competing_videos = Column(Integer, nullable=True)
    average_competitor_views = Column(Integer, nullable=True)

    # Market gap analysis
    content_gap_identified = Column(Text, nullable=True)  # Description of the gap
    recommended_angle = Column(Text, nullable=True)  # Suggested approach

    # Scoring weights used
    weights = Column(Float, nullable=True)  # JSON of weights if custom

    # Trend prediction
    trend_prediction = Column(Text, nullable=True)  # "rising", "stable", "declining"
    confidence_score = Column(Float, nullable=True)  # 0-1 confidence in prediction

    # Recommendations
    is_recommended = Column(Integer, default=0)  # Boolean flag for top opportunities

    # Relationships
    video = relationship("Video", back_populates="opportunity_score")

    def __repr__(self):
        return f"<OpportunityScore(id={self.id}, video_id={self.video_id}, score={self.overall_score})>"
