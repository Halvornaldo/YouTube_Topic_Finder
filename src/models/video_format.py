"""Video format model - format predictions from Robot 4 (Format Classifier)."""

from sqlalchemy import Column, Integer, Float, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from src.models.base import Base, TimestampMixin


class VideoFormatType(str, enum.Enum):
    """Predicted video format types."""
    TUTORIAL = "tutorial"
    LISTICLE = "listicle"
    NEWS = "news"
    REVIEW = "review"
    COMPARISON = "comparison"
    VLOG = "vlog"
    INTERVIEW = "interview"
    EXPLAINER = "explainer"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"


class VideoFormat(Base, TimestampMixin):
    """
    Video format predictions from Robot 4.

    Uses audio transcription and NLP analysis to predict
    the winning video format.
    """

    __tablename__ = "video_formats"

    # Foreign key
    video_id = Column(Integer, ForeignKey("videos.id"), unique=True, nullable=False, index=True)

    # Primary format prediction
    predicted_format = Column(Enum(VideoFormatType), nullable=False, index=True)
    confidence = Column(Float, nullable=True)  # 0-1 confidence score

    # Alternative formats (JSON array)
    alternative_formats = Column(JSON, nullable=True)  # [{format: "tutorial", confidence: 0.8}, ...]

    # Transcript analysis
    transcript_available = Column(Integer, default=0)  # Boolean
    transcript_length = Column(Integer, nullable=True)  # Character count
    transcript_summary = Column(Text, nullable=True)  # Brief summary

    # Format indicators (detected patterns)
    has_step_by_step = Column(Integer, default=0)  # Tutorial indicator
    has_numbered_list = Column(Integer, default=0)  # Listicle indicator
    has_comparison = Column(Integer, default=0)  # Comparison indicator
    has_personal_story = Column(Integer, default=0)  # Vlog indicator

    # NLP analysis
    key_phrases = Column(JSON, nullable=True)  # List of key phrases
    sentiment = Column(Text, nullable=True)  # Overall sentiment
    pacing = Column(Text, nullable=True)  # "fast", "medium", "slow"

    # Audio characteristics
    audio_duration_seconds = Column(Integer, nullable=True)
    speaking_rate = Column(Float, nullable=True)  # Words per minute
    silence_ratio = Column(Float, nullable=True)  # Ratio of silence to speech

    # Format-specific metadata
    structure_detected = Column(JSON, nullable=True)  # Detected structure elements
    hook_effectiveness = Column(Float, nullable=True)  # 0-1 score for intro hook

    # Processing info
    transcription_model = Column(Text, nullable=True)  # e.g., "whisper-large"
    processing_time_seconds = Column(Float, nullable=True)

    # Relationships
    video = relationship("Video", back_populates="video_format")

    def __repr__(self):
        return f"<VideoFormat(id={self.id}, video_id={self.video_id}, format={self.predicted_format})>"
