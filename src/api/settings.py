"""API endpoints for application settings management."""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime

from src.config.database import get_db
from src.services.config_manager import ConfigManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for request/response
class SettingBase(BaseModel):
    """Base setting model."""
    key: str = Field(..., min_length=1, max_length=200)
    value: str = Field(..., min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    data_type: str = Field(default='string', pattern='^(string|integer|float|boolean|json)$')
    requires_restart: bool = Field(default=False)
    description: Optional[str] = None


class SettingCreate(SettingBase):
    """Model for creating a new setting."""
    changed_by: str = Field(default='api', max_length=100)
    change_reason: Optional[str] = None


class SettingUpdate(BaseModel):
    """Model for updating a setting."""
    value: str = Field(..., min_length=1)
    changed_by: str = Field(default='api', max_length=100)
    change_reason: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    requires_restart: Optional[bool] = None
    description: Optional[str] = None


class SettingResponse(BaseModel):
    """Model for setting response."""
    key: str
    value: Any  # Typed value (not string)
    raw_value: str  # Original string value
    category: Optional[str]
    data_type: str
    requires_restart: bool
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingListResponse(BaseModel):
    """Response for listing settings."""
    settings: List[SettingResponse]
    total: int
    category: Optional[str]


class ReloadResponse(BaseModel):
    """Response for reload operation."""
    status: str
    message: str
    reloaded_count: int
    settings_requiring_restart: List[str]


class HistoryEntry(BaseModel):
    """History entry model."""
    key: str
    change_type: str
    changed_by: str
    changed_at: datetime
    old_value: Optional[Any]
    new_value: Optional[Any]
    requires_restart: bool


class HistoryResponse(BaseModel):
    """Response for history listing."""
    changes: List[HistoryEntry]
    total: int


@router.get("", response_model=SettingListResponse)
async def get_all_settings(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    Get all application settings.

    Optionally filter by category.

    Args:
        category: Optional category filter (e.g., 'robot1', 'api', 'processing')
        db: Database session

    Returns:
        List of settings
    """
    try:
        config_manager = ConfigManager(db)
        settings_dict = config_manager.get_all(category=category)

        # Convert to response format
        settings_list = []
        for key, typed_value in settings_dict.items():
            metadata = config_manager._metadata.get(key)
            if metadata:
                settings_list.append(SettingResponse(
                    key=key,
                    value=typed_value,
                    raw_value=metadata.value,
                    category=metadata.category,
                    data_type=metadata.data_type,
                    requires_restart=metadata.requires_restart,
                    description=metadata.description,
                    is_active=bool(metadata.is_active),
                    created_at=metadata.created_at,
                    updated_at=metadata.updated_at
                ))

        return SettingListResponse(
            settings=settings_list,
            total=len(settings_list),
            category=category
        )

    except Exception as e:
        logger.error(f"Error retrieving settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific setting by key.

    Args:
        key: Setting key
        db: Database session

    Returns:
        Setting details
    """
    try:
        config_manager = ConfigManager(db)

        # Check if setting exists
        if key not in config_manager._metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Setting '{key}' not found"
            )

        metadata = config_manager._metadata[key]
        typed_value = config_manager.get(key)

        return SettingResponse(
            key=key,
            value=typed_value,
            raw_value=metadata.value,
            category=metadata.category,
            data_type=metadata.data_type,
            requires_restart=metadata.requires_restart,
            description=metadata.description,
            is_active=bool(metadata.is_active),
            created_at=metadata.created_at,
            updated_at=metadata.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving setting '{key}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=SettingResponse, status_code=201)
async def create_setting(
    setting: SettingCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new setting.

    Args:
        setting: Setting data
        db: Database session

    Returns:
        Created setting
    """
    try:
        config_manager = ConfigManager(db)

        # Check if setting already exists
        if setting.key in config_manager._metadata:
            raise HTTPException(
                status_code=409,
                detail=f"Setting '{setting.key}' already exists"
            )

        # Create setting
        success = config_manager.set(
            key=setting.key,
            value=setting.value,
            changed_by=setting.changed_by,
            change_reason=setting.change_reason,
            category=setting.category,
            requires_restart=setting.requires_restart,
            description=setting.description
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to create setting"
            )

        # Return created setting
        return await get_setting(setting.key, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating setting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    update: SettingUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing setting.

    Args:
        key: Setting key
        update: Update data
        db: Database session

    Returns:
        Updated setting
    """
    try:
        config_manager = ConfigManager(db)

        # Check if setting exists
        if key not in config_manager._metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Setting '{key}' not found"
            )

        # Get existing metadata to preserve fields not being updated
        existing = config_manager._metadata[key]

        # Update setting
        success = config_manager.set(
            key=key,
            value=update.value,
            changed_by=update.changed_by,
            change_reason=update.change_reason,
            category=update.category if update.category is not None else existing.category,
            requires_restart=update.requires_restart if update.requires_restart is not None else existing.requires_restart,
            description=update.description if update.description is not None else existing.description
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update setting"
            )

        # Return updated setting
        return await get_setting(key, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating setting '{key}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{key}")
async def delete_setting(
    key: str,
    changed_by: str = Query(default='api'),
    change_reason: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Delete a setting (marks as inactive).

    Args:
        key: Setting key
        changed_by: Who is making the change
        change_reason: Optional reason for deletion
        db: Database session

    Returns:
        Success message
    """
    try:
        config_manager = ConfigManager(db)

        # Check if setting exists
        if key not in config_manager._metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Setting '{key}' not found"
            )

        # Delete setting
        success = config_manager.delete(
            key=key,
            changed_by=changed_by,
            change_reason=change_reason
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete setting"
            )

        return {
            "status": "success",
            "message": f"Setting '{key}' deleted successfully",
            "key": key
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting setting '{key}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload", response_model=ReloadResponse)
async def reload_settings(
    force: bool = Query(default=False, description="Force reload all settings including those requiring restart"),
    db: Session = Depends(get_db)
):
    """
    Reload hot-reloadable settings from database.

    Args:
        force: If True, reload all settings including those requiring restart
        db: Database session

    Returns:
        Reload status and count
    """
    try:
        config_manager = ConfigManager(db)

        # Reload settings
        reloaded_count = config_manager.reload(force=force)

        # Get settings requiring restart
        restart_required = config_manager.get_settings_requiring_restart()

        return ReloadResponse(
            status="success",
            message=f"Reloaded {reloaded_count} settings",
            reloaded_count=reloaded_count,
            settings_requiring_restart=restart_required
        )

    except Exception as e:
        logger.error(f"Error reloading settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/changes", response_model=HistoryResponse)
async def get_setting_history(
    since: Optional[datetime] = Query(None, description="Get changes since this timestamp"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of entries to return"),
    db: Session = Depends(get_db)
):
    """
    Get change history for settings.

    Args:
        since: Optional timestamp to get changes since
        limit: Maximum number of entries (1-1000)
        db: Database session

    Returns:
        List of historical changes
    """
    try:
        config_manager = ConfigManager(db)

        # Get changes
        changes = config_manager.get_changed_settings(since=since)

        # Limit results
        changes = changes[:limit]

        # Convert to response format
        history_entries = [
            HistoryEntry(
                key=change['key'],
                change_type=change['change_type'],
                changed_by=change['changed_by'],
                changed_at=change['changed_at'],
                old_value=change['old_value'],
                new_value=change['new_value'],
                requires_restart=change['requires_restart']
            )
            for change in changes
        ]

        return HistoryResponse(
            changes=history_entries,
            total=len(history_entries)
        )

    except Exception as e:
        logger.error(f"Error retrieving setting history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meta/restart-required")
async def get_restart_required_settings(
    db: Session = Depends(get_db)
):
    """
    Get list of settings that require application restart.

    Args:
        db: Database session

    Returns:
        List of setting keys requiring restart
    """
    try:
        config_manager = ConfigManager(db)
        restart_required = config_manager.get_settings_requiring_restart()

        return {
            "settings": restart_required,
            "count": len(restart_required),
            "message": "These settings require application restart to take effect"
        }

    except Exception as e:
        logger.error(f"Error retrieving restart-required settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
