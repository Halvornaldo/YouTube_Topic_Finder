"""Application settings and environment configuration."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Supports .env file for local development.
    """

    # Application
    APP_NAME: str = "YouTube Topic Finder"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/youtube_topic_finder"
    )
    SQL_ECHO: bool = Field(default=False)

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = Field(default=10)

    # API Keys
    YOUTUBE_API_KEY: Optional[str] = Field(default=None)
    GOOGLE_ADS_DEVELOPER_TOKEN: Optional[str] = Field(default=None)
    GOOGLE_ADS_CLIENT_ID: Optional[str] = Field(default=None)
    GOOGLE_ADS_CLIENT_SECRET: Optional[str] = Field(default=None)
    GOOGLE_ADS_REFRESH_TOKEN: Optional[str] = Field(default=None)
    REDDIT_CLIENT_ID: Optional[str] = Field(default=None)
    REDDIT_CLIENT_SECRET: Optional[str] = Field(default=None)
    REDDIT_USER_AGENT: str = Field(default="YouTubeTopicFinder/1.0")
    OPENAI_API_KEY: Optional[str] = Field(default=None)

    # Configuration
    DEFAULT_NICHE: str = Field(default="ai_tech")
    CONFIG_DIR: str = Field(default="config/niches")

    # Robot 1 (Horizon Scanner) Settings
    ROBOT1_GOOGLE_TRENDS_ENABLED: bool = Field(default=True)
    ROBOT1_REDDIT_ENABLED: bool = Field(default=True)
    ROBOT1_MAX_TOPICS_PER_RUN: int = Field(default=20)

    # Robot 2 (SERP Scraper) Settings
    ROBOT2_MAX_VIDEOS_PER_QUERY: int = Field(default=50)
    ROBOT2_PLAYWRIGHT_ENABLED: bool = Field(default=True)
    ROBOT2_API_FALLBACK: bool = Field(default=True)
    ROBOT2_REQUEST_DELAY_SECONDS: int = Field(default=2)

    # Robot 3 (Metric Analyzer) Settings
    ROBOT3_YOUTUBE_API_ENABLED: bool = Field(default=True)
    ROBOT3_GOOGLE_ADS_ENABLED: bool = Field(default=False)
    ROBOT3_BATCH_SIZE: int = Field(default=50)

    # Robot 4 (Format Classifier) Settings
    ROBOT4_WHISPER_MODEL: str = Field(default="base")  # tiny, base, small, medium, large
    ROBOT4_MAX_AUDIO_LENGTH_SECONDS: int = Field(default=600)  # 10 minutes
    ROBOT4_DOWNLOAD_AUDIO: bool = Field(default=True)

    # Rate Limiting
    YOUTUBE_API_DAILY_QUOTA: int = Field(default=10000)
    REDDIT_API_REQUESTS_PER_MINUTE: int = Field(default=60)

    # Processing
    MAX_CONCURRENT_JOBS: int = Field(default=5)
    JOB_TIMEOUT_SECONDS: int = Field(default=3600)  # 1 hour

    # Paths
    LOG_DIR: str = Field(default="logs")
    DOWNLOAD_DIR: str = Field(default="downloads")
    TEMP_DIR: str = Field(default="temp")

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
