"""API endpoints for robot operations."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from src.config.database import get_db
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response models
class HorizonScanRequest(BaseModel):
    """Request to run Robot 1 (Horizon Scanner)."""
    niche_id: int = Field(..., description="ID of the niche configuration to use", gt=0)
    max_topics: Optional[int] = Field(None, description="Maximum topics to discover", gt=0, le=200)


class HorizonScanResponse(BaseModel):
    """Response from Robot 1."""
    job_id: int
    status: str
    message: str
    niche_id: int
    niche_name: Optional[str] = None


class SerpScrapeRequest(BaseModel):
    """Request to run Robot 2 (SERP Scraper)."""
    topic_ids: Optional[List[int]] = None
    seed_topic_id: Optional[int] = None
    max_videos: Optional[int] = 50


class MetricAnalysisRequest(BaseModel):
    """Request to run Robot 3 (Metric Analyzer)."""
    video_ids: Optional[List[int]] = None
    search_query_id: Optional[int] = None


class FormatClassificationRequest(BaseModel):
    """Request to run Robot 4 (Format Classifier)."""
    video_id: int


class PipelineRequest(BaseModel):
    """Request to run full pipeline."""
    niche_id: int = Field(..., description="ID of the niche configuration to use", gt=0)
    max_topics: Optional[int] = Field(10, gt=0)
    max_videos_per_topic: Optional[int] = Field(20, gt=0)


async def _run_horizon_scanner_async(db: Session, niche_id: int, max_topics: Optional[int] = None):
    """
    Helper function to run Horizon Scanner asynchronously.

    Args:
        db: Database session
        niche_id: Niche configuration ID
        max_topics: Max topics to discover
    """
    try:
        from src.robots.horizon_scanner import HorizonScanner

        scanner = HorizonScanner(db)
        result = await scanner.run(niche_id, max_topics)

        logger.info(f"Horizon Scanner completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in background horizon scanner task: {e}", exc_info=True)
        # Error is already handled in scanner.run() and broadcast to SSE
        raise


@router.post("/horizon-scanner/run", response_model=HorizonScanResponse)
async def run_horizon_scanner(
    request: HorizonScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Run Robot 1: Horizon Scanner.

    Discovers trending seed topics from Google Trends and Reddit based on niche configuration.

    The scanner will:
    - Create a job status record
    - Load niche configuration from database
    - Scan Google Trends (if enabled for niche)
    - Scan Reddit (if enabled for niche)
    - Save discovered topics to database
    - Broadcast real-time progress via SSE

    Returns immediately with job ID. Monitor progress via:
    - GET /api/jobs/{job_id}
    - SSE /api/events/stream?event_types=job_progress

    Args:
        request: Scan request with niche_id and optional max_topics
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Response with job_id for monitoring
    """
    try:
        from src.robots.horizon_scanner import HorizonScanner
        from src.models.niche_config import NicheConfig
        from sqlalchemy import select

        # Validate niche exists
        stmt = select(NicheConfig).where(
            NicheConfig.id == request.niche_id,
            NicheConfig.is_active == 1
        )
        niche_config = db.execute(stmt).scalar_one_or_none()

        if not niche_config:
            raise HTTPException(
                status_code=404,
                detail=f"Niche configuration not found or inactive: ID {request.niche_id}"
            )

        # Create scanner and start job in background
        # Note: We need to run the async function in the event loop
        background_tasks.add_task(
            _run_horizon_scanner_async,
            db,
            request.niche_id,
            request.max_topics
        )

        return HorizonScanResponse(
            job_id=0,  # Will be set by scanner.run()
            status="queued",
            message=f"Horizon scanner queued for niche: {niche_config.name}",
            niche_id=request.niche_id,
            niche_name=niche_config.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queueing horizon scanner: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/serp-scraper/run")
async def run_serp_scraper(
    request: SerpScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Run Robot 2: SERP Scraper.

    Scrapes YouTube search results for candidate videos.

    Status: Not yet implemented
    """
    # TODO: Implement Robot 2
    raise HTTPException(status_code=501, detail="Robot 2 not yet implemented")


@router.post("/metric-analyzer/run")
async def run_metric_analyzer(
    request: MetricAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Run Robot 3: Metric Analyzer.

    Calculates opportunity scores for videos.

    Status: Not yet implemented
    """
    # TODO: Implement Robot 3
    raise HTTPException(status_code=501, detail="Robot 3 not yet implemented")


@router.post("/format-classifier/run")
async def run_format_classifier(
    request: FormatClassificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Run Robot 4: Format Classifier.

    Predicts video format from transcript analysis.

    Status: Not yet implemented
    """
    # TODO: Implement Robot 4
    raise HTTPException(status_code=501, detail="Robot 4 not yet implemented")


@router.post("/pipeline/run")
async def run_full_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Run full pipeline: All robots in sequence.

    1. Horizon Scanner -> 2. SERP Scraper -> 3. Metric Analyzer -> 4. Format Classifier

    Status: Not yet implemented
    """
    # TODO: Implement full pipeline orchestration
    raise HTTPException(status_code=501, detail="Full pipeline not yet implemented")


@router.get("/status")
async def get_robots_status(db: Session = Depends(get_db)):
    """
    Get status of all robots.

    Returns:
        Status information for each robot
    """
    from src.models.job_status import JobStatus
    from sqlalchemy import select, func

    # Get recent job counts by robot type
    robot_statuses = {}

    for robot_type in ['robot1', 'robot2', 'robot3', 'robot4']:
        # Count running jobs
        running_count = db.execute(
            select(func.count()).select_from(JobStatus).where(
                JobStatus.job_type == robot_type,
                JobStatus.status == 'running'
            )
        ).scalar()

        # Get most recent job
        latest_job = db.execute(
            select(JobStatus).where(
                JobStatus.job_type == robot_type
            ).order_by(JobStatus.created_at.desc()).limit(1)
        ).scalar_one_or_none()

        robot_statuses[robot_type] = {
            'running_jobs': running_count,
            'status': 'running' if running_count > 0 else 'idle',
            'last_run': latest_job.created_at.isoformat() if latest_job else None,
            'last_status': latest_job.status if latest_job else None
        }

    return {
        'robots': robot_statuses,
        'total_running_jobs': sum(r['running_jobs'] for r in robot_statuses.values())
    }
