"""Niche configuration model - loaded YAML configurations."""

from sqlalchemy import Column, String, Text, JSON, Float, Integer
from src.models.base import Base, TimestampMixin


class NicheConfig(Base, TimestampMixin):
    """
    Niche configurations loaded from YAML files.

    Stores parsed configuration data for different content niches.
    """

    __tablename__ = "niche_configs"

    # Basic info
    niche_name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)

    # Keywords and topics
    keywords = Column(JSON, nullable=False)  # List of keywords
    seed_topics = Column(JSON, nullable=True)  # Predefined topics

    # Source configuration
    google_trends_enabled = Column(Integer, default=1)  # Boolean
    google_trends_weight = Column(Float, default=0.5)
    reddit_enabled = Column(Integer, default=1)  # Boolean
    reddit_weight = Column(Float, default=0.5)
    reddit_subreddits = Column(JSON, nullable=True)  # List of subreddits

    # Scoring thresholds
    min_search_volume = Column(Integer, nullable=True)
    max_competition = Column(Float, nullable=True)
    min_opportunity_score = Column(Float, nullable=True)

    # Format preferences
    preferred_formats = Column(JSON, nullable=True)  # List of format types
    excluded_formats = Column(JSON, nullable=True)

    # Regional settings
    target_regions = Column(JSON, nullable=True)  # List of region codes
    target_languages = Column(JSON, nullable=True)  # List of language codes

    # Custom settings
    custom_settings = Column(JSON, nullable=True)  # Additional niche-specific settings

    # File metadata
    config_file_path = Column(String(500), nullable=True)
    config_hash = Column(String(64), nullable=True)  # SHA-256 of file content

    # Template and ownership tracking
    is_template = Column(Integer, default=0, nullable=False)  # Boolean: is this a read-only template?
    created_by = Column(String(100), nullable=True)  # 'system', 'user', or user ID
    version = Column(Integer, default=1, nullable=False)  # Version number for tracking changes

    # Status
    is_active = Column(Integer, default=1)  # Boolean

    def __repr__(self):
        return f"<NicheConfig(id={self.id}, niche='{self.niche_name}', template={bool(self.is_template)}, active={bool(self.is_active)})>"
