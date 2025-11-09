"""API endpoints for niche configuration management."""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from src.config.niche_loader import niche_loader
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class NicheListResponse(BaseModel):
    """List of available niches."""
    niches: List[str]
    default: str


class NicheDetailResponse(BaseModel):
    """Detailed niche configuration."""
    name: str
    display_name: str
    description: str
    keywords: List[str]
    seed_topics: List[str]
    google_trends_enabled: bool
    reddit_enabled: bool
    reddit_subreddits: List[str]
    min_search_volume: int
    max_competition: float
    min_opportunity_score: float
    preferred_formats: List[str]
    target_regions: List[str]


@router.get("/", response_model=NicheListResponse)
async def list_niches():
    """
    Get list of all available niches.

    Returns niche names and the default niche.
    """
    try:
        niches = niche_loader.list_niches()
        from src.config.settings import settings

        return NicheListResponse(
            niches=niches,
            default=settings.DEFAULT_NICHE
        )
    except Exception as e:
        logger.error(f"Error listing niches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{niche_name}", response_model=NicheDetailResponse)
async def get_niche_details(niche_name: str):
    """
    Get detailed configuration for a specific niche.

    Args:
        niche_name: Name of the niche (e.g., "ai_tech")
    """
    try:
        config = niche_loader.get_config(niche_name)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Niche '{niche_name}' not found"
            )

        return NicheDetailResponse(
            name=config.name,
            display_name=config.display_name,
            description=config.description,
            keywords=config.keywords,
            seed_topics=config.seed_topics,
            google_trends_enabled=config.google_trends.get("enabled", True),
            reddit_enabled=config.reddit.get("enabled", True),
            reddit_subreddits=config.reddit.get("subreddits", []),
            min_search_volume=config.min_search_volume,
            max_competition=config.max_competition,
            min_opportunity_score=config.min_opportunity_score,
            preferred_formats=config.preferred_formats,
            target_regions=config.target_regions,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting niche details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_niches():
    """
    Reload all niche configurations from disk.

    Useful after modifying YAML files.
    """
    try:
        niche_loader.reload()
        return {
            "status": "success",
            "message": "Niche configurations reloaded",
            "niches": niche_loader.list_niches()
        }
    except Exception as e:
        logger.error(f"Error reloading niches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
