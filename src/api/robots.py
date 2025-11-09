"""API endpoints for robot operations."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from src.config.database import get_db
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response models
class HorizonScanRequest(BaseModel):
    """Request to run Robot 1 (Horizon Scanner)."""
    niche: str = "ai_tech"
    max_topics: Optional[int] = 20


class HorizonScanResponse(BaseModel):
    """Response from Robot 1."""
    job_id: int
    status: str
    message: str
    topics_found: Optional[int] = None


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
    niche: str = "ai_tech"
    max_topics: Optional[int] = 10
    max_videos_per_topic: Optional[int] = 20


@router.post("/horizon-scanner/run", response_model=HorizonScanResponse)
async def run_horizon_scanner(
    request: HorizonScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Run Robot 1: Horizon Scanner.

    Discovers trending seed topics from Google Trends and Reddit.
    """
    try:
        from src.robots.horizon_scanner import HorizonScanner

        scanner = HorizonScanner(db)

        # Run in background
        background_tasks.add_task(scanner.run, request.niche, request.max_topics)

        return HorizonScanResponse(
            job_id=0,  # TODO: Implement job tracking
            status="started",
            message=f"Horizon scanner started for niche: {request.niche}",
        )
    except Exception as e:
        logger.error(f"Error running horizon scanner: {e}", exc_info=True)
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
    """
    # TODO: Implement full pipeline orchestration
    raise HTTPException(status_code=501, detail="Full pipeline not yet implemented")
