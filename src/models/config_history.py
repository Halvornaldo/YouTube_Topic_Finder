"""Configuration history model - version control for all configuration changes."""

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON
from datetime import datetime
from src.models.base import Base, TimestampMixin


class ConfigHistory(Base, TimestampMixin):
    """
    Configuration version history and audit trail.

    Tracks all changes to configurations (niches, settings, robot parameters)
    with full diff support and rollback capability.
    """

    __tablename__ = "config_history"

    # Configuration identification
    config_type = Column(String(100), nullable=False, index=True)  # 'niche', 'setting', 'robot_param', 'system'
    config_id = Column(Integer, nullable=True, index=True)  # ID of the config (null for system-wide changes)
    config_key = Column(String(200), nullable=True, index=True)  # Key/name of the config

    # Version tracking
    version = Column(Integer, nullable=False, default=1)

    # Change tracking
    changes_json = Column(JSON, nullable=False)  # Full diff of what changed
    previous_value = Column(JSON, nullable=True)  # Previous value before change
    new_value = Column(JSON, nullable=True)  # New value after change

    # Change metadata
    change_type = Column(String(50), nullable=False)  # 'create', 'update', 'delete', 'rollback'
    change_reason = Column(Text, nullable=True)  # Optional reason for change

    # Audit information
    changed_by = Column(String(100), nullable=True)  # User ID, 'system', or 'api'
    # Note: changed_at is provided by TimestampMixin as created_at

    # Rollback support
    rollback_available = Column(Boolean, default=True, nullable=False)
    rollback_data = Column(JSON, nullable=True)  # Full snapshot for rollback

    # Additional context
    source = Column(String(100), nullable=True)  # 'dashboard', 'api', 'cli', 'automation'
    ip_address = Column(String(50), nullable=True)  # IP address of change origin

    def __repr__(self):
        return f"<ConfigHistory(id={self.id}, type='{self.config_type}', key='{self.config_key}', version={self.version})>"

    @staticmethod
    def create_change(config_type: str, config_id: int, config_key: str,
                     change_type: str, changes: dict, previous_value=None,
                     new_value=None, changed_by: str = 'system',
                     change_reason: str = None, rollback_data: dict = None):
        """
        Create a new configuration history entry.

        Args:
            config_type: Type of configuration
            config_id: ID of the configuration
            config_key: Key/name of the configuration
            change_type: Type of change (create/update/delete/rollback)
            changes: Dictionary of changes
            previous_value: Previous value before change
            new_value: New value after change
            changed_by: Who made the change
            change_reason: Reason for the change
            rollback_data: Full snapshot for rollback

        Returns:
            ConfigHistory instance
        """
        return ConfigHistory(
            config_type=config_type,
            config_id=config_id,
            config_key=config_key,
            change_type=change_type,
            changes_json=changes,
            previous_value=previous_value,
            new_value=new_value,
            changed_by=changed_by,
            change_reason=change_reason,
            rollback_data=rollback_data,
            rollback_available=(rollback_data is not None)
        )

    def can_rollback(self):
        """Check if this change can be rolled back."""
        return self.rollback_available and self.rollback_data is not None

    def get_change_summary(self):
        """Get a human-readable summary of changes."""
        if not self.changes_json:
            return "No changes recorded"

        summary = []
        for key, value in self.changes_json.items():
            if isinstance(value, dict) and 'old' in value and 'new' in value:
                summary.append(f"{key}: '{value['old']}' → '{value['new']}'")
            else:
                summary.append(f"{key}: {value}")

        return ", ".join(summary)
