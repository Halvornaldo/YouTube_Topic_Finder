"""Configuration Manager with hot-reload support.

This service manages runtime configuration with support for hot-reloading
settings that don't require application restart.
"""

import logging
from typing import Any, Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.models.app_setting import AppSetting
from src.models.config_history import ConfigHistory

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Singleton configuration manager with hot-reload support.

    This class manages runtime configuration by:
    1. Loading settings from database into memory cache
    2. Providing type-safe get/set operations
    3. Supporting hot-reload for settings that don't require restart
    4. Tracking configuration changes in history
    5. Validating settings before applying changes

    Usage:
        config_manager = ConfigManager(db_session)

        # Get a setting with type conversion
        max_jobs = config_manager.get("MAX_CONCURRENT_JOBS", default=5)

        # Update a setting
        config_manager.set("MAX_CONCURRENT_JOBS", 10, changed_by="user_123")

        # Reload hot-reloadable settings
        config_manager.reload()
    """

    _instance = None
    _initialized = False

    def __new__(cls, db: Optional[Session] = None):
        """Singleton pattern - ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, db: Optional[Session] = None):
        """Initialize the configuration manager.

        Args:
            db: SQLAlchemy database session
        """
        # Only initialize once
        if self._initialized:
            return

        if db is None:
            raise ValueError("Database session is required for initialization")

        self.db = db
        self._cache: Dict[str, Any] = {}
        self._metadata: Dict[str, AppSetting] = {}
        self._last_reload: Optional[datetime] = None

        # Load all settings into cache
        self._load_settings()
        self._initialized = True

        logger.info("ConfigManager initialized with %d settings", len(self._cache))

    def _load_settings(self):
        """Load all settings from database into memory cache."""
        try:
            stmt = select(AppSetting).where(AppSetting.is_active == True)
            settings = self.db.execute(stmt).scalars().all()

            for setting in settings:
                # Store typed value in cache
                self._cache[setting.key] = setting.get_typed_value()
                # Store metadata as dictionary (not ORM object to avoid session issues)
                self._metadata[setting.key] = {
                    'category': setting.category,
                    'data_type': setting.data_type,
                    'requires_restart': setting.requires_restart,
                    'description': setting.description
                }

            self._last_reload = datetime.utcnow()
            logger.debug("Loaded %d settings from database", len(settings))

        except Exception as e:
            logger.error("Failed to load settings from database: %s", str(e))
            raise

    def get(self, key: str, default: Any = None, category: Optional[str] = None) -> Any:
        """Get a setting value with type conversion.

        Args:
            key: Setting key
            default: Default value if setting doesn't exist
            category: Optional category filter

        Returns:
            Setting value with appropriate type, or default if not found
        """
        # Check if setting exists in cache
        if key in self._cache:
            # Optionally filter by category
            if category is not None:
                metadata = self._metadata.get(key)
                if metadata and metadata.get('category') != category:
                    return default
            return self._cache[key]

        # Setting not found, return default
        logger.debug("Setting '%s' not found, returning default: %s", key, default)
        return default

    def get_all(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get all settings, optionally filtered by category.

        Args:
            category: Optional category to filter by

        Returns:
            Dictionary of key-value pairs
        """
        if category is None:
            return self._cache.copy()

        # Filter by category
        filtered = {}
        for key, value in self._cache.items():
            metadata = self._metadata.get(key)
            if metadata and metadata.get('category') == category:
                filtered[key] = value

        return filtered

    def set(
        self,
        key: str,
        value: Any,
        changed_by: str = "system",
        change_reason: Optional[str] = None,
        category: Optional[str] = None,
        requires_restart: bool = False,
        description: Optional[str] = None
    ) -> bool:
        """Set a setting value and track the change.

        Args:
            key: Setting key
            value: New value (will be converted to string for storage)
            changed_by: Who made the change (user ID, 'system', 'api')
            change_reason: Optional reason for the change
            category: Setting category (e.g., 'robot1', 'api', 'processing')
            requires_restart: Whether this change requires app restart
            description: Human-readable description of the setting

        Returns:
            True if setting was updated successfully, False otherwise
        """
        try:
            # Get existing setting or create new one
            stmt = select(AppSetting).where(AppSetting.key == key)
            existing = self.db.execute(stmt).scalar_one_or_none()

            # Determine data type
            data_type = self._infer_data_type(value)

            # Convert value to string for storage
            str_value = str(value) if not isinstance(value, str) else value

            if existing:
                # Track old value for history
                old_value = existing.get_typed_value()

                # Update existing setting
                existing.value = str_value
                existing.data_type = data_type
                existing.requires_restart = requires_restart
                if category:
                    existing.category = category
                if description:
                    existing.description = description
                existing.updated_at = datetime.utcnow()

                # Create history entry
                history = ConfigHistory.create_change(
                    config_type='app_setting',
                    config_id=existing.id,
                    config_key=key,
                    change_type='update',
                    changes={key: {'old': old_value, 'new': value}},
                    previous_value={'value': old_value, 'data_type': existing.data_type},
                    new_value={'value': value, 'data_type': data_type},
                    changed_by=changed_by,
                    change_reason=change_reason,
                    rollback_data={
                        'key': key,
                        'value': existing.value,
                        'data_type': existing.data_type,
                        'category': existing.category,
                        'requires_restart': existing.requires_restart
                    }
                )

            else:
                # Create new setting
                existing = AppSetting(
                    key=key,
                    value=str_value,
                    data_type=data_type,
                    category=category or 'general',
                    requires_restart=requires_restart,
                    description=description,
                    is_active=True
                )
                self.db.add(existing)

                # Create history entry
                history = ConfigHistory.create_change(
                    config_type='app_setting',
                    config_id=None,  # Will be set after commit
                    config_key=key,
                    change_type='create',
                    changes={key: {'new': value}},
                    new_value={'value': value, 'data_type': data_type},
                    changed_by=changed_by,
                    change_reason=change_reason
                )

            # Add history and commit
            self.db.add(history)
            self.db.commit()

            # Update cache if hot-reloadable
            if not requires_restart:
                self._cache[key] = value
                self._metadata[key] = existing
                logger.info("Setting '%s' updated and hot-reloaded", key)
            else:
                logger.warning(
                    "Setting '%s' updated but requires restart to take effect",
                    key
                )

            return True

        except Exception as e:
            logger.error("Failed to set setting '%s': %s", key, str(e))
            self.db.rollback()
            return False

    def reload(self, force: bool = False) -> int:
        """Reload hot-reloadable settings from database.

        Args:
            force: If True, reload all settings including those requiring restart

        Returns:
            Number of settings reloaded
        """
        try:
            count = 0
            stmt = select(AppSetting).where(AppSetting.is_active == True)

            if not force:
                # Only reload settings that don't require restart
                stmt = stmt.where(AppSetting.requires_restart == False)

            settings = self.db.execute(stmt).scalars().all()

            for setting in settings:
                old_value = self._cache.get(setting.key)
                new_value = setting.get_typed_value()

                # Only update if value changed
                if old_value != new_value:
                    self._cache[setting.key] = new_value
                    self._metadata[setting.key] = setting
                    count += 1
                    logger.debug(
                        "Reloaded setting '%s': %s -> %s",
                        setting.key, old_value, new_value
                    )

            self._last_reload = datetime.utcnow()
            logger.info("Reloaded %d settings", count)
            return count

        except Exception as e:
            logger.error("Failed to reload settings: %s", str(e))
            return 0

    def delete(
        self,
        key: str,
        changed_by: str = "system",
        change_reason: Optional[str] = None
    ) -> bool:
        """Delete a setting (marks as inactive).

        Args:
            key: Setting key to delete
            changed_by: Who made the change
            change_reason: Optional reason for deletion

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            stmt = select(AppSetting).where(AppSetting.key == key)
            setting = self.db.execute(stmt).scalar_one_or_none()

            if not setting:
                logger.warning("Cannot delete setting '%s': not found", key)
                return False

            # Store old value for history
            old_value = setting.get_typed_value()

            # Mark as inactive instead of deleting
            setting.is_active = False
            setting.updated_at = datetime.utcnow()

            # Create history entry
            history = ConfigHistory.create_change(
                config_type='app_setting',
                config_id=setting.id,
                config_key=key,
                change_type='delete',
                changes={key: {'old': old_value, 'new': None}},
                previous_value={'value': old_value},
                new_value=None,
                changed_by=changed_by,
                change_reason=change_reason,
                rollback_data={
                    'key': key,
                    'value': setting.value,
                    'data_type': setting.data_type,
                    'category': setting.category,
                    'requires_restart': setting.requires_restart
                }
            )

            self.db.add(history)
            self.db.commit()

            # Remove from cache
            if key in self._cache:
                del self._cache[key]
            if key in self._metadata:
                del self._metadata[key]

            logger.info("Setting '%s' deleted", key)
            return True

        except Exception as e:
            logger.error("Failed to delete setting '%s': %s", key, str(e))
            self.db.rollback()
            return False

    def get_settings_requiring_restart(self) -> List[str]:
        """Get list of settings that require restart.

        Returns:
            List of setting keys that require restart
        """
        return [
            key for key, metadata in self._metadata.items()
            if metadata.get('requires_restart')
        ]

    def get_changed_settings(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get settings that have changed since a given time.

        Args:
            since: Optional datetime to check changes since. If None, uses last reload time.

        Returns:
            List of changed settings with metadata
        """
        check_time = since or self._last_reload
        if check_time is None:
            return []

        try:
            stmt = (
                select(ConfigHistory)
                .where(ConfigHistory.config_type == 'app_setting')
                .where(ConfigHistory.created_at > check_time)
                .order_by(ConfigHistory.created_at.desc())
            )

            changes = self.db.execute(stmt).scalars().all()

            return [
                {
                    'key': change.config_key,
                    'change_type': change.change_type,
                    'changed_by': change.changed_by,
                    'changed_at': change.created_at,
                    'old_value': change.previous_value,
                    'new_value': change.new_value,
                    'requires_restart': self._metadata.get(change.config_key, {}).get('requires_restart', False)
                }
                for change in changes
            ]

        except Exception as e:
            logger.error("Failed to get changed settings: %s", str(e))
            return []

    @staticmethod
    def _infer_data_type(value: Any) -> str:
        """Infer data type from Python value.

        Args:
            value: Python value

        Returns:
            Data type string ('string', 'integer', 'float', 'boolean', 'json')
        """
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, (dict, list)):
            return 'json'
        else:
            return 'string'

    def __repr__(self):
        """String representation of ConfigManager."""
        return (
            f"<ConfigManager(settings={len(self._cache)}, "
            f"last_reload={self._last_reload})>"
        )
