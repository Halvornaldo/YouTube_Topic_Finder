"""API endpoints for niche configuration management."""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
import tempfile
import os

from src.config.database import get_db
from src.services.niche_service import NicheService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for request/response
class NicheBase(BaseModel):
    """Base niche model."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = Field(..., min_items=1)
    seed_topics: Optional[List[str]] = None
    google_trends_enabled: bool = True
    google_trends_weight: float = Field(default=0.5, ge=0, le=1)
    reddit_enabled: bool = True
    reddit_weight: float = Field(default=0.5, ge=0, le=1)
    reddit_subreddits: Optional[List[str]] = None
    min_search_volume: Optional[int] = Field(None, ge=0)
    max_competition: Optional[float] = Field(None, ge=0, le=1)
    min_opportunity_score: Optional[float] = Field(None, ge=0, le=100)
    preferred_formats: Optional[List[str]] = None
    excluded_formats: Optional[List[str]] = None
    target_regions: Optional[List[str]] = None
    target_languages: Optional[List[str]] = None
    custom_settings: Optional[Dict[str, Any]] = None


class NicheCreate(NicheBase):
    """Model for creating a new niche."""
    niche_name: str = Field(..., min_length=1, max_length=100, pattern="^[a-zA-Z0-9_-]+$")
    is_template: bool = False
    created_by: str = Field(default="user", max_length=100)
    change_reason: Optional[str] = None


class NicheUpdate(BaseModel):
    """Model for updating a niche."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = Field(None, min_items=1)
    seed_topics: Optional[List[str]] = None
    google_trends_enabled: Optional[bool] = None
    google_trends_weight: Optional[float] = Field(None, ge=0, le=1)
    reddit_enabled: Optional[bool] = None
    reddit_weight: Optional[float] = Field(None, ge=0, le=1)
    reddit_subreddits: Optional[List[str]] = None
    min_search_volume: Optional[int] = Field(None, ge=0)
    max_competition: Optional[float] = Field(None, ge=0, le=1)
    min_opportunity_score: Optional[float] = Field(None, ge=0, le=100)
    preferred_formats: Optional[List[str]] = None
    excluded_formats: Optional[List[str]] = None
    target_regions: Optional[List[str]] = None
    target_languages: Optional[List[str]] = None
    custom_settings: Optional[Dict[str, Any]] = None
    changed_by: str = Field(default="user", max_length=100)
    change_reason: Optional[str] = None


class NicheResponse(BaseModel):
    """Model for niche response."""
    id: int
    niche_name: str
    display_name: Optional[str]
    description: Optional[str]
    keywords: List[str]
    seed_topics: Optional[List[str]]
    google_trends_enabled: bool
    google_trends_weight: float
    reddit_enabled: bool
    reddit_weight: float
    reddit_subreddits: Optional[List[str]]
    min_search_volume: Optional[int]
    max_competition: Optional[float]
    min_opportunity_score: Optional[float]
    preferred_formats: Optional[List[str]]
    excluded_formats: Optional[List[str]]
    target_regions: Optional[List[str]]
    target_languages: Optional[List[str]]
    custom_settings: Optional[Dict[str, Any]]
    is_template: bool
    created_by: Optional[str]
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NicheListResponse(BaseModel):
    """Response for listing niches."""
    niches: List[NicheResponse]
    total: int
    templates_only: bool
    user_only: bool


class ValidationResult(BaseModel):
    """Validation result model."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    niche_name: str
    niche_id: int


@router.get("", response_model=NicheListResponse)
async def list_niches(
    include_inactive: bool = Query(default=False, description="Include inactive niches"),
    templates_only: bool = Query(default=False, description="Only return template niches"),
    user_only: bool = Query(default=False, description="Only return user-created niches"),
    db: Session = Depends(get_db)
):
    """
    Get all niche configurations.

    Filter by template status and active status.

    Args:
        include_inactive: Include inactive niches
        templates_only: Only return template niches
        user_only: Only return user-created niches
        db: Database session

    Returns:
        List of niches
    """
    try:
        niche_service = NicheService(db)
        niches = niche_service.get_all(
            include_inactive=include_inactive,
            templates_only=templates_only,
            user_only=user_only
        )

        # Convert to response format
        niche_responses = [
            NicheResponse(
                id=n.id,
                niche_name=n.niche_name,
                display_name=n.display_name,
                description=n.description,
                keywords=n.keywords,
                seed_topics=n.seed_topics,
                google_trends_enabled=bool(n.google_trends_enabled),
                google_trends_weight=n.google_trends_weight,
                reddit_enabled=bool(n.reddit_enabled),
                reddit_weight=n.reddit_weight,
                reddit_subreddits=n.reddit_subreddits,
                min_search_volume=n.min_search_volume,
                max_competition=n.max_competition,
                min_opportunity_score=n.min_opportunity_score,
                preferred_formats=n.preferred_formats,
                excluded_formats=n.excluded_formats,
                target_regions=n.target_regions,
                target_languages=n.target_languages,
                custom_settings=n.custom_settings,
                is_template=bool(n.is_template),
                created_by=n.created_by,
                version=n.version,
                is_active=bool(n.is_active),
                created_at=n.created_at,
                updated_at=n.updated_at
            )
            for n in niches
        ]

        return NicheListResponse(
            niches=niche_responses,
            total=len(niche_responses),
            templates_only=templates_only,
            user_only=user_only
        )

    except Exception as e:
        logger.error(f"Error listing niches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{niche_id}", response_model=NicheResponse)
async def get_niche(
    niche_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific niche by ID.

    Args:
        niche_id: Niche ID
        db: Database session

    Returns:
        Niche details
    """
    try:
        niche_service = NicheService(db)
        niche = niche_service.get_by_id(niche_id)

        if not niche:
            raise HTTPException(
                status_code=404,
                detail=f"Niche with ID {niche_id} not found"
            )

        return NicheResponse(
            id=niche.id,
            niche_name=niche.niche_name,
            display_name=niche.display_name,
            description=niche.description,
            keywords=niche.keywords,
            seed_topics=niche.seed_topics,
            google_trends_enabled=bool(niche.google_trends_enabled),
            google_trends_weight=niche.google_trends_weight,
            reddit_enabled=bool(niche.reddit_enabled),
            reddit_weight=niche.reddit_weight,
            reddit_subreddits=niche.reddit_subreddits,
            min_search_volume=niche.min_search_volume,
            max_competition=niche.max_competition,
            min_opportunity_score=niche.min_opportunity_score,
            preferred_formats=niche.preferred_formats,
            excluded_formats=niche.excluded_formats,
            target_regions=niche.target_regions,
            target_languages=niche.target_languages,
            custom_settings=niche.custom_settings,
            is_template=bool(niche.is_template),
            created_by=niche.created_by,
            version=niche.version,
            is_active=bool(niche.is_active),
            created_at=niche.created_at,
            updated_at=niche.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting niche {niche_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=NicheResponse, status_code=201)
async def create_niche(
    niche: NicheCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new niche configuration.

    Args:
        niche: Niche data
        db: Database session

    Returns:
        Created niche
    """
    try:
        niche_service = NicheService(db)

        # Create niche
        created = niche_service.create(
            niche_name=niche.niche_name,
            keywords=niche.keywords,
            display_name=niche.display_name,
            description=niche.description,
            seed_topics=niche.seed_topics,
            google_trends_enabled=niche.google_trends_enabled,
            google_trends_weight=niche.google_trends_weight,
            reddit_enabled=niche.reddit_enabled,
            reddit_weight=niche.reddit_weight,
            reddit_subreddits=niche.reddit_subreddits,
            min_search_volume=niche.min_search_volume,
            max_competition=niche.max_competition,
            min_opportunity_score=niche.min_opportunity_score,
            preferred_formats=niche.preferred_formats,
            excluded_formats=niche.excluded_formats,
            target_regions=niche.target_regions,
            target_languages=niche.target_languages,
            custom_settings=niche.custom_settings,
            is_template=niche.is_template,
            created_by=niche.created_by,
            change_reason=niche.change_reason
        )

        if not created:
            raise HTTPException(
                status_code=409,
                detail=f"Niche '{niche.niche_name}' already exists"
            )

        return await get_niche(created.id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating niche: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{niche_id}", response_model=NicheResponse)
async def update_niche(
    niche_id: int,
    update: NicheUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing niche configuration.

    Args:
        niche_id: Niche ID
        update: Update data
        db: Database session

    Returns:
        Updated niche
    """
    try:
        niche_service = NicheService(db)

        # Prepare update dict (only include fields that were provided)
        update_data = {}
        for field, value in update.dict(exclude_unset=True).items():
            if field not in ('changed_by', 'change_reason'):
                update_data[field] = value

        # Update niche
        updated = niche_service.update(
            niche_id=niche_id,
            changed_by=update.changed_by,
            change_reason=update.change_reason,
            **update_data
        )

        if not updated:
            raise HTTPException(
                status_code=404,
                detail=f"Niche with ID {niche_id} not found or is a template"
            )

        return await get_niche(niche_id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating niche {niche_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{niche_id}")
async def delete_niche(
    niche_id: int,
    changed_by: str = Query(default="user"),
    change_reason: Optional[str] = Query(default=None),
    hard_delete: bool = Query(default=False, description="Permanently delete instead of marking inactive"),
    db: Session = Depends(get_db)
):
    """
    Delete a niche configuration.

    Args:
        niche_id: Niche ID
        changed_by: Who is making the change
        change_reason: Reason for deletion
        hard_delete: If True, permanently delete
        db: Database session

    Returns:
        Success message
    """
    try:
        niche_service = NicheService(db)

        success = niche_service.delete(
            niche_id=niche_id,
            changed_by=changed_by,
            change_reason=change_reason,
            hard_delete=hard_delete
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Niche with ID {niche_id} not found or is a template"
            )

        return {
            "status": "success",
            "message": f"Niche deleted successfully",
            "niche_id": niche_id,
            "hard_delete": hard_delete
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting niche {niche_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{niche_id}/duplicate", response_model=NicheResponse, status_code=201)
async def duplicate_niche(
    niche_id: int,
    new_name: str = Query(..., min_length=1, max_length=100, pattern="^[a-zA-Z0-9_-]+$"),
    created_by: str = Query(default="user"),
    as_template: bool = Query(default=False),
    db: Session = Depends(get_db)
):
    """
    Duplicate an existing niche configuration.

    Args:
        niche_id: ID of niche to duplicate
        new_name: Name for the new niche
        created_by: Who is creating the duplicate
        as_template: Whether to create as a template
        db: Database session

    Returns:
        New niche configuration
    """
    try:
        niche_service = NicheService(db)

        duplicated = niche_service.duplicate(
            niche_id=niche_id,
            new_name=new_name,
            created_by=created_by,
            as_template=as_template
        )

        if not duplicated:
            raise HTTPException(
                status_code=404,
                detail=f"Niche with ID {niche_id} not found or name '{new_name}' already exists"
            )

        return await get_niche(duplicated.id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating niche {niche_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{niche_id}/validate", response_model=ValidationResult)
async def validate_niche(
    niche_id: int,
    db: Session = Depends(get_db)
):
    """
    Validate a niche configuration.

    Checks for required fields, valid ranges, and configuration integrity.

    Args:
        niche_id: Niche ID
        db: Database session

    Returns:
        Validation result with errors and warnings
    """
    try:
        niche_service = NicheService(db)
        result = niche_service.validate_config(niche_id)

        if result.get('valid') is None:
            raise HTTPException(
                status_code=404,
                detail=f"Niche with ID {niche_id} not found"
            )

        return ValidationResult(
            valid=result['valid'],
            errors=result['errors'],
            warnings=result['warnings'],
            niche_name=result['niche_name'],
            niche_id=result['niche_id']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating niche {niche_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{niche_id}/export")
async def export_niche_yaml(
    niche_id: int,
    db: Session = Depends(get_db)
):
    """
    Export a niche configuration to YAML file.

    Args:
        niche_id: Niche ID
        db: Database session

    Returns:
        YAML file download
    """
    try:
        niche_service = NicheService(db)

        # Get niche to get its name
        niche = niche_service.get_by_id(niche_id)
        if not niche:
            raise HTTPException(
                status_code=404,
                detail=f"Niche with ID {niche_id} not found"
            )

        # Create temporary file
        temp_dir = tempfile.gettempdir()
        output_file = os.path.join(temp_dir, f"{niche.niche_name}.yaml")

        # Export to YAML
        success = niche_service.export_to_yaml(niche_id, output_file)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to export niche to YAML"
            )

        return FileResponse(
            path=output_file,
            filename=f"{niche.niche_name}.yaml",
            media_type="application/x-yaml"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting niche {niche_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", response_model=NicheResponse, status_code=201)
async def import_niche_yaml(
    file: UploadFile = File(...),
    as_template: bool = Query(default=True),
    created_by: str = Query(default="system"),
    db: Session = Depends(get_db)
):
    """
    Import a niche configuration from YAML file.

    Args:
        file: YAML file to import
        as_template: Whether to import as template
        created_by: Who is importing this niche
        db: Database session

    Returns:
        Imported niche configuration
    """
    try:
        # Validate file type
        if not file.filename.endswith('.yaml') and not file.filename.endswith('.yml'):
            raise HTTPException(
                status_code=400,
                detail="File must be a YAML file (.yaml or .yml)"
            )

        # Save uploaded file temporarily
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, file.filename)

        with open(temp_file, 'wb') as f:
            content = await file.read()
            f.write(content)

        # Import from YAML
        niche_service = NicheService(db)
        imported = niche_service.import_from_yaml(
            file_path=temp_file,
            as_template=as_template,
            created_by=created_by
        )

        # Clean up temp file
        os.remove(temp_file)

        if not imported:
            raise HTTPException(
                status_code=500,
                detail="Failed to import niche from YAML"
            )

        return await get_niche(imported.id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing niche from YAML: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/name/{niche_name}", response_model=NicheResponse)
async def get_niche_by_name(
    niche_name: str,
    db: Session = Depends(get_db)
):
    """
    Get a niche by name.

    Args:
        niche_name: Niche name
        db: Database session

    Returns:
        Niche details
    """
    try:
        niche_service = NicheService(db)
        niche = niche_service.get_by_name(niche_name)

        if not niche:
            raise HTTPException(
                status_code=404,
                detail=f"Niche '{niche_name}' not found"
            )

        return await get_niche(niche.id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting niche by name '{niche_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/seed", response_model=Dict[str, Any])
async def seed_templates(
    overwrite: bool = Query(default=False, description="Overwrite existing templates"),
    clear: bool = Query(default=False, description="Clear existing templates before seeding"),
    db: Session = Depends(get_db)
):
    """
    Seed niche templates from YAML files into the database.

    Loads all YAML files from the config/niches directory and creates
    database records marked as templates.

    Args:
        overwrite: If True, update existing templates
        clear: If True, clear all existing templates first
        db: Database session

    Returns:
        Seeding results with counts and any errors
    """
    try:
        from src.services.template_seeder import TemplateSeeder

        seeder = TemplateSeeder(db)

        # Clear existing templates if requested
        if clear:
            cleared_count = seeder.clear_templates()
            logger.info(f"Cleared {cleared_count} existing templates")

        # Seed templates
        results = seeder.seed_all_templates(overwrite=overwrite)

        return {
            "status": "success",
            "message": f"Seeded {results['created'] + results['updated']} templates",
            "results": results,
            "total_templates": seeder.get_template_count()
        }

    except Exception as e:
        logger.error(f"Error seeding templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/validate", response_model=Dict[str, Any])
async def validate_templates(
    db: Session = Depends(get_db)
):
    """
    Validate all YAML template files without importing them.

    Checks for syntax errors and required fields in all YAML files.

    Args:
        db: Database session

    Returns:
        Validation results
    """
    try:
        from src.services.template_seeder import TemplateSeeder

        seeder = TemplateSeeder(db)
        results = seeder.validate_templates()

        return {
            "status": "success" if not results['invalid_files'] else "warning",
            "validation_results": results
        }

    except Exception as e:
        logger.error(f"Error validating templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/count", response_model=Dict[str, int])
async def get_template_count(
    db: Session = Depends(get_db)
):
    """
    Get count of template niche configurations in database.

    Args:
        db: Database session

    Returns:
        Count of templates
    """
    try:
        from src.services.template_seeder import TemplateSeeder

        seeder = TemplateSeeder(db)
        count = seeder.get_template_count()

        return {
            "template_count": count
        }

    except Exception as e:
        logger.error(f"Error getting template count: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
