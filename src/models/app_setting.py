"""Application settings model - all configurable system settings."""

from sqlalchemy import Column, String, Text, Boolean
from src.models.base import Base, TimestampMixin


class AppSetting(Base, TimestampMixin):
    """
    Application settings with hot-reload support.

    Stores all configurable settings including robot behavior,
    API keys, processing limits, and system preferences.
    """

    __tablename__ = "app_settings"

    # Setting identification
    key = Column(String(200), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)

    # Categorization and metadata
    category = Column(String(100), nullable=True, index=True)  # 'robot1', 'robot2', 'processing', 'api_keys', etc.
    data_type = Column(String(50), nullable=False, default='string')  # 'string', 'integer', 'boolean', 'float', 'json'

    # Hot-reload configuration
    requires_restart = Column(Boolean, default=False, nullable=False)

    # Documentation
    description = Column(Text, nullable=True)
    default_value = Column(Text, nullable=True)

    # Validation (optional JSON schema)
    validation_rules = Column(Text, nullable=True)  # JSON string with validation rules

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<AppSetting(key='{self.key}', value='{self.value}', category='{self.category}')>"

    def get_typed_value(self):
        """
        Convert string value to appropriate Python type based on data_type.

        Returns:
            The value converted to the appropriate type
        """
        if self.data_type == 'integer':
            return int(self.value)
        elif self.data_type == 'float':
            return float(self.value)
        elif self.data_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'json':
            import json
            return json.loads(self.value)
        else:  # string
            return self.value
