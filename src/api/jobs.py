"""API endpoints for job monitoring and management."""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from src.config.database import get_db
from src.models.job_status import JobStatus
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for request/response
class JobResponse(BaseModel):
    """Model for job response."""
    id: int
    job_type: str
    status: str
    progress_percent: int
    current_step: Optional[str]
    total_steps: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    result_summary: Optional[Dict[str, Any]]
    config_snapshot: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    # Computed properties
    duration_seconds: Optional[int]
    is_running: bool
    is_completed: bool
    is_failed: bool

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Response for listing jobs."""
    jobs: List[JobResponse]
    total: int
    page: int
    per_page: int
    job_type_filter: Optional[str]
    status_filter: Optional[str]


class JobStatsResponse(BaseModel):
    """Job statistics response."""
    total_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int
    cancelled_jobs: int
    average_duration_seconds: Optional[float]
    by_type: Dict[str, int]
    by_status: Dict[str, int]


class CancelJobResponse(BaseModel):
    """Response for canceling a job."""
    status: str
    message: str
    job_id: int
    previous_status: str


class CleanupResponse(BaseModel):
    """Response for cleanup operation."""
    status: str
    message: str
    deleted_count: int
    cleanup_criteria: str


@router.get("", response_model=JobListResponse)
async def list_jobs(
    job_type: Optional[str] = Query(None, description="Filter by job type (e.g., 'robot1', 'robot2')"),
    status: Optional[str] = Query(None, description="Filter by status (pending, running, completed, failed, cancelled)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get all jobs with optional filtering.

    Args:
        job_type: Filter by job type
        status: Filter by status
        page: Page number for pagination
        per_page: Items per page
        db: Database session

    Returns:
        Paginated list of jobs
    """
    try:
        # Build query
        stmt = select(JobStatus)

        # Apply filters
        filters = []
        if job_type:
            filters.append(JobStatus.job_type == job_type)
        if status:
            filters.append(JobStatus.status == status)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Count total
        count_stmt = select(func.count()).select_from(JobStatus)
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = db.execute(count_stmt).scalar()

        # Apply pagination and ordering
        stmt = stmt.order_by(JobStatus.created_at.desc())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)

        # Execute query
        jobs = db.execute(stmt).scalars().all()

        # Convert to response format
        job_responses = [
            JobResponse(
                id=job.id,
                job_type=job.job_type,
                status=job.status,
                progress_percent=job.progress_percent,
                current_step=job.current_step,
                total_steps=job.total_steps,
                started_at=job.started_at,
                completed_at=job.completed_at,
                error_message=job.error_message,
                result_summary=job.result_summary,
                config_snapshot=job.config_snapshot,
                created_at=job.created_at,
                updated_at=job.updated_at,
                duration_seconds=job.duration_seconds,
                is_running=job.is_running,
                is_completed=job.is_completed,
                is_failed=job.is_failed
            )
            for job in jobs
        ]

        return JobListResponse(
            jobs=job_responses,
            total=total,
            page=page,
            per_page=per_page,
            job_type_filter=job_type,
            status_filter=status
        )

    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=JobStatsResponse)
async def get_job_stats(
    db: Session = Depends(get_db)
):
    """
    Get job statistics.

    Provides counts by status and type, plus average duration.

    Args:
        db: Database session

    Returns:
        Job statistics
    """
    try:
        # Total jobs
        total_jobs = db.execute(select(func.count()).select_from(JobStatus)).scalar()

        # By status
        running_jobs = db.execute(
            select(func.count()).select_from(JobStatus).where(JobStatus.status == 'running')
        ).scalar()

        completed_jobs = db.execute(
            select(func.count()).select_from(JobStatus).where(JobStatus.status == 'completed')
        ).scalar()

        failed_jobs = db.execute(
            select(func.count()).select_from(JobStatus).where(JobStatus.status == 'failed')
        ).scalar()

        pending_jobs = db.execute(
            select(func.count()).select_from(JobStatus).where(JobStatus.status == 'pending')
        ).scalar()

        cancelled_jobs = db.execute(
            select(func.count()).select_from(JobStatus).where(JobStatus.status == 'cancelled')
        ).scalar()

        # Average duration for completed jobs
        completed_with_duration = db.execute(
            select(JobStatus).where(
                and_(
                    JobStatus.status == 'completed',
                    JobStatus.started_at.isnot(None),
                    JobStatus.completed_at.isnot(None)
                )
            )
        ).scalars().all()

        avg_duration = None
        if completed_with_duration:
            durations = [job.duration_seconds for job in completed_with_duration if job.duration_seconds]
            avg_duration = sum(durations) / len(durations) if durations else None

        # By type
        type_counts = db.execute(
            select(JobStatus.job_type, func.count(JobStatus.id))
            .group_by(JobStatus.job_type)
        ).all()

        by_type = {job_type: count for job_type, count in type_counts}

        # By status (detailed)
        status_counts = db.execute(
            select(JobStatus.status, func.count(JobStatus.id))
            .group_by(JobStatus.status)
        ).all()

        by_status = {status: count for status, count in status_counts}

        return JobStatsResponse(
            total_jobs=total_jobs,
            running_jobs=running_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            pending_jobs=pending_jobs,
            cancelled_jobs=cancelled_jobs,
            average_duration_seconds=avg_duration,
            by_type=by_type,
            by_status=by_status
        )

    except Exception as e:
        logger.error(f"Error getting job stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific job by ID.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        Job details
    """
    try:
        stmt = select(JobStatus).where(JobStatus.id == job_id)
        job = db.execute(stmt).scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID {job_id} not found"
            )

        return JobResponse(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            progress_percent=job.progress_percent,
            current_step=job.current_step,
            total_steps=job.total_steps,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            result_summary=job.result_summary,
            config_snapshot=job.config_snapshot,
            created_at=job.created_at,
            updated_at=job.updated_at,
            duration_seconds=job.duration_seconds,
            is_running=job.is_running,
            is_completed=job.is_completed,
            is_failed=job.is_failed
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/cancel", response_model=CancelJobResponse)
async def cancel_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Cancel a running or pending job.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        Cancellation status
    """
    try:
        stmt = select(JobStatus).where(JobStatus.id == job_id)
        job = db.execute(stmt).scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID {job_id} not found"
            )

        # Can only cancel pending or running jobs
        if job.status not in ('pending', 'running'):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job with status '{job.status}'. Only pending or running jobs can be cancelled."
            )

        previous_status = job.status

        # Cancel the job
        job.cancel()
        db.commit()

        logger.info(f"Job {job_id} cancelled (was {previous_status})")

        return CancelJobResponse(
            status="success",
            message=f"Job cancelled successfully",
            job_id=job_id,
            previous_status=previous_status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/type/{job_type}", response_model=JobListResponse)
async def get_jobs_by_type(
    job_type: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all jobs of a specific type.

    Args:
        job_type: Job type (e.g., 'robot1', 'robot2')
        status: Optional status filter
        page: Page number
        per_page: Items per page
        db: Database session

    Returns:
        Paginated list of jobs
    """
    return await list_jobs(
        job_type=job_type,
        status=status,
        page=page,
        per_page=per_page,
        db=db
    )


@router.get("/running/all", response_model=JobListResponse)
async def get_running_jobs(
    db: Session = Depends(get_db)
):
    """
    Get all currently running jobs.

    Args:
        db: Database session

    Returns:
        List of running jobs
    """
    return await list_jobs(
        status='running',
        page=1,
        per_page=100,
        db=db
    )


@router.delete("/cleanup", response_model=CleanupResponse)
async def cleanup_old_jobs(
    older_than_days: int = Query(default=30, ge=1, le=365, description="Delete jobs older than N days"),
    status: Optional[str] = Query(None, description="Only delete jobs with this status (completed, failed, cancelled)"),
    db: Session = Depends(get_db)
):
    """
    Clean up old completed/failed/cancelled jobs.

    Args:
        older_than_days: Delete jobs older than this many days
        status: Optional status filter (only completed, failed, or cancelled allowed)
        db: Database session

    Returns:
        Cleanup result
    """
    try:
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

        # Build delete query
        filters = [JobStatus.created_at < cutoff_date]

        # Only allow deleting completed, failed, or cancelled jobs
        if status:
            if status not in ('completed', 'failed', 'cancelled'):
                raise HTTPException(
                    status_code=400,
                    detail="Can only delete jobs with status: completed, failed, or cancelled"
                )
            filters.append(JobStatus.status == status)
        else:
            # Default: only delete completed, failed, or cancelled
            filters.append(JobStatus.status.in_(['completed', 'failed', 'cancelled']))

        # Count before deletion
        count_stmt = select(func.count()).select_from(JobStatus).where(and_(*filters))
        count = db.execute(count_stmt).scalar()

        # Delete jobs
        stmt = select(JobStatus).where(and_(*filters))
        jobs_to_delete = db.execute(stmt).scalars().all()

        for job in jobs_to_delete:
            db.delete(job)

        db.commit()

        criteria = f"older than {older_than_days} days"
        if status:
            criteria += f", status={status}"

        logger.info(f"Cleaned up {count} old jobs ({criteria})")

        return CleanupResponse(
            status="success",
            message=f"Deleted {count} old jobs",
            deleted_count=count,
            cleanup_criteria=criteria
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up jobs: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent/{count}", response_model=JobListResponse)
async def get_recent_jobs(
    count: int = Path(..., ge=1, le=100, description="Number of recent jobs to return"),
    db: Session = Depends(get_db)
):
    """
    Get most recent jobs.

    Args:
        count: Number of jobs to return
        db: Database session

    Returns:
        List of recent jobs
    """
    return await list_jobs(
        page=1,
        per_page=count,
        db=db
    )
