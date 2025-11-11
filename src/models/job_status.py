"""Job status model - real-time job tracking and monitoring."""

from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from datetime import datetime
from src.models.base import Base, TimestampMixin


class JobStatus(Base, TimestampMixin):
    """
    Job tracking for real-time monitoring.

    Tracks execution of all robot jobs with progress updates,
    status changes, and result summaries.
    """

    __tablename__ = "job_status"

    # Job identification
    job_type = Column(String(100), nullable=False, index=True)  # 'horizon_scan', 'serp_scrape', 'metric_analysis', 'format_classification'

    # Status tracking
    status = Column(String(50), nullable=False, default='pending', index=True)  # 'pending', 'running', 'completed', 'failed', 'cancelled'

    # Progress tracking
    progress_percent = Column(Integer, default=0, nullable=False)  # 0-100
    current_step = Column(String(200), nullable=True)  # Human-readable current step
    total_steps = Column(Integer, nullable=True)  # Total number of steps (if known)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    error_trace = Column(Text, nullable=True)  # Full stack trace for debugging

    # Results
    result_summary = Column(JSON, nullable=True)  # Stats about what was found/processed

    # Configuration snapshot
    config_snapshot = Column(JSON, nullable=True)  # Configuration used for this job

    # Related entities (optional foreign keys)
    niche_id = Column(Integer, nullable=True)  # If job is for a specific niche
    parent_job_id = Column(Integer, nullable=True)  # If this job was triggered by another job

    def __repr__(self):
        return f"<JobStatus(id={self.id}, type='{self.job_type}', status='{self.status}', progress={self.progress_percent}%)>"

    def start(self):
        """Mark job as started."""
        self.status = 'running'
        self.started_at = datetime.utcnow()
        self.progress_percent = 0

    def update_progress(self, percent: int, step: str = None):
        """Update job progress."""
        self.progress_percent = min(100, max(0, percent))
        if step:
            self.current_step = step

    def complete(self, result_summary: dict = None):
        """Mark job as completed successfully."""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.progress_percent = 100
        if result_summary:
            self.result_summary = result_summary

    def fail(self, error_message: str, error_trace: str = None):
        """Mark job as failed."""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if error_trace:
            self.error_trace = error_trace

    def cancel(self):
        """Mark job as cancelled."""
        self.status = 'cancelled'
        self.completed_at = datetime.utcnow()

    @property
    def duration_seconds(self):
        """Calculate job duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()

    @property
    def is_running(self):
        """Check if job is currently running."""
        return self.status == 'running'

    @property
    def is_completed(self):
        """Check if job completed successfully."""
        return self.status == 'completed'

    @property
    def is_failed(self):
        """Check if job failed."""
        return self.status == 'failed'
