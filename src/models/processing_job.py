"""Processing job model - tracks job queue and processing status."""

from sqlalchemy import Column, String, Integer, Text, JSON, Enum, Float
from src.models.base import Base, TimestampMixin
import enum


class JobType(str, enum.Enum):
    """Type of processing job."""
    HORIZON_SCAN = "horizon_scan"  # Robot 1
    SERP_SCRAPE = "serp_scrape"  # Robot 2
    METRIC_ANALYSIS = "metric_analysis"  # Robot 3
    FORMAT_CLASSIFICATION = "format_classification"  # Robot 4
    FULL_PIPELINE = "full_pipeline"  # All robots


class JobStatus(str, enum.Enum):
    """Status of the job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingJob(Base, TimestampMixin):
    """
    Processing jobs for the queue system.

    Tracks execution of each robot and full pipeline runs.
    """

    __tablename__ = "processing_jobs"

    # Job identification
    job_type = Column(Enum(JobType), nullable=False, index=True)
    job_status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)

    # Job parameters
    niche = Column(String(100), nullable=True, index=True)
    parameters = Column(JSON, nullable=True)  # Job-specific parameters

    # Execution tracking
    started_at = Column(Integer, nullable=True)  # Timestamp
    completed_at = Column(Integer, nullable=True)  # Timestamp
    execution_time_seconds = Column(Float, nullable=True)

    # Progress tracking
    total_items = Column(Integer, nullable=True)
    processed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)

    # Results
    result_summary = Column(JSON, nullable=True)  # Summary of results
    output_file = Column(String(500), nullable=True)  # Path to output file if applicable

    # Error handling
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Priority and scheduling
    priority = Column(Integer, default=5)  # 1-10, higher = more priority
    scheduled_for = Column(Integer, nullable=True)  # Timestamp for scheduled jobs

    # Related entities
    related_entity_type = Column(String(50), nullable=True)  # e.g., "seed_topic", "video"
    related_entity_id = Column(Integer, nullable=True)

    # Worker info
    worker_id = Column(String(100), nullable=True)  # ID of worker that processed the job
    worker_hostname = Column(String(200), nullable=True)

    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, type={self.job_type}, status={self.job_status})>"
