"""API endpoints for opportunity discovery results."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from src.config.database import get_db
from src.models import OpportunityScore, Video
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# Response models
class OpportunityResponse(BaseModel):
    """Opportunity score response."""
    id: int
    video_id: int
    video_title: str
    video_url: str
    overall_score: float
    competition_level: str
    content_gap: Optional[str]
    recommended_angle: Optional[str]
    is_recommended: bool

    class Config:
        from_attributes = True


class TopicAnalysisResponse(BaseModel):
    """Full topic analysis response."""
    topic: str
    opportunity_score: float
    search_volume: Optional[int]
    competition: str
    predicted_format: Optional[str]
    format_confidence: Optional[float]
    content_gap: Optional[str]
    suggested_angle: Optional[str]
    keywords: List[str]


@router.get("", response_model=List[OpportunityResponse])
async def get_opportunities(
    limit: int = Query(default=10, le=100),
    min_score: float = Query(default=60.0, ge=0, le=100),
    niche: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get top opportunities.

    Returns opportunities sorted by score (descending).
    """
    try:
        query = db.query(OpportunityScore, Video).join(
            Video, OpportunityScore.video_id == Video.id
        ).filter(
            OpportunityScore.overall_score >= min_score
        )

        # TODO: Add niche filtering once we add niche field to videos

        opportunities = query.order_by(
            OpportunityScore.overall_score.desc()
        ).limit(limit).all()

        results = []
        for opp, video in opportunities:
            results.append(OpportunityResponse(
                id=opp.id,
                video_id=video.id,
                video_title=video.title,
                video_url=f"https://www.youtube.com/watch?v={video.video_id}",
                overall_score=opp.overall_score,
                competition_level=opp.competition_level.value if opp.competition_level else "unknown",
                content_gap=opp.content_gap_identified,
                recommended_angle=opp.recommended_angle,
                is_recommended=bool(opp.is_recommended),
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching opportunities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommended", response_model=List[OpportunityResponse])
async def get_recommended_opportunities(
    limit: int = Query(default=10, le=100),
    db: Session = Depends(get_db)
):
    """Get only recommended opportunities (is_recommended = True)."""
    try:
        opportunities = db.query(OpportunityScore, Video).join(
            Video, OpportunityScore.video_id == Video.id
        ).filter(
            OpportunityScore.is_recommended == 1
        ).order_by(
            OpportunityScore.overall_score.desc()
        ).limit(limit).all()

        results = []
        for opp, video in opportunities:
            results.append(OpportunityResponse(
                id=opp.id,
                video_id=video.id,
                video_title=video.title,
                video_url=f"https://www.youtube.com/watch?v={video.video_id}",
                overall_score=opp.overall_score,
                competition_level=opp.competition_level.value if opp.competition_level else "unknown",
                content_gap=opp.content_gap_identified,
                recommended_angle=opp.recommended_angle,
                is_recommended=True,
            ))

        return results

    except Exception as e:
        logger.error(f"Error fetching recommended opportunities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{opportunity_id}")
async def get_opportunity_details(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific opportunity."""
    opportunity = db.query(OpportunityScore).filter(
        OpportunityScore.id == opportunity_id
    ).first()

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    video = db.query(Video).filter(Video.id == opportunity.video_id).first()

    return {
        "opportunity": opportunity,
        "video": video,
    }
