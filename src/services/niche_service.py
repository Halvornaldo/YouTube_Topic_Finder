"""Niche Configuration Service.

This service handles CRUD operations for niche configurations,
including template management, validation, and import/export.
"""

import logging
import hashlib
import yaml
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from src.models.niche_config import NicheConfig
from src.models.config_history import ConfigHistory

logger = logging.getLogger(__name__)


class NicheService:
    """
    Service for managing niche configurations.

    Handles:
    - CRUD operations for niches
    - Template vs user-created niche distinction
    - YAML import/export
    - Configuration validation
    - Version tracking and history
    """

    def __init__(self, db: Session):
        """Initialize the niche service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_all(
        self,
        include_inactive: bool = False,
        templates_only: bool = False,
        user_only: bool = False
    ) -> List[NicheConfig]:
        """Get all niche configurations.

        Args:
            include_inactive: Include inactive niches
            templates_only: Only return template niches
            user_only: Only return user-created niches

        Returns:
            List of niche configurations
        """
        try:
            stmt = select(NicheConfig)

            # Filter by active status
            if not include_inactive:
                stmt = stmt.where(NicheConfig.is_active == 1)

            # Filter by template status
            if templates_only:
                stmt = stmt.where(NicheConfig.is_template == 1)
            elif user_only:
                stmt = stmt.where(NicheConfig.is_template == 0)

            # Order by name
            stmt = stmt.order_by(NicheConfig.niche_name)

            niches = self.db.execute(stmt).scalars().all()
            logger.debug("Retrieved %d niches", len(niches))
            return niches

        except Exception as e:
            logger.error("Failed to retrieve niches: %s", str(e))
            return []

    def get_by_id(self, niche_id: int) -> Optional[NicheConfig]:
        """Get a niche by ID.

        Args:
            niche_id: Niche ID

        Returns:
            Niche configuration or None if not found
        """
        try:
            stmt = select(NicheConfig).where(NicheConfig.id == niche_id)
            niche = self.db.execute(stmt).scalar_one_or_none()
            return niche
        except Exception as e:
            logger.error("Failed to get niche %d: %s", niche_id, str(e))
            return None

    def get_by_name(self, niche_name: str) -> Optional[NicheConfig]:
        """Get a niche by name.

        Args:
            niche_name: Niche name

        Returns:
            Niche configuration or None if not found
        """
        try:
            stmt = select(NicheConfig).where(NicheConfig.niche_name == niche_name)
            niche = self.db.execute(stmt).scalar_one_or_none()
            return niche
        except Exception as e:
            logger.error("Failed to get niche '%s': %s", niche_name, str(e))
            return None

    def create(
        self,
        niche_name: str,
        keywords: List[str],
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        seed_topics: Optional[List[str]] = None,
        google_trends_enabled: bool = True,
        google_trends_weight: float = 0.5,
        reddit_enabled: bool = True,
        reddit_weight: float = 0.5,
        reddit_subreddits: Optional[List[str]] = None,
        min_search_volume: Optional[int] = None,
        max_competition: Optional[float] = None,
        min_opportunity_score: Optional[float] = None,
        preferred_formats: Optional[List[str]] = None,
        excluded_formats: Optional[List[str]] = None,
        target_regions: Optional[List[str]] = None,
        target_languages: Optional[List[str]] = None,
        custom_settings: Optional[Dict[str, Any]] = None,
        is_template: bool = False,
        created_by: str = "user",
        change_reason: Optional[str] = None
    ) -> Optional[NicheConfig]:
        """Create a new niche configuration.

        Args:
            niche_name: Unique niche name
            keywords: List of keywords
            display_name: Human-readable display name
            description: Niche description
            seed_topics: Predefined topics
            google_trends_enabled: Enable Google Trends
            google_trends_weight: Google Trends weight
            reddit_enabled: Enable Reddit
            reddit_weight: Reddit weight
            reddit_subreddits: List of subreddits
            min_search_volume: Minimum search volume threshold
            max_competition: Maximum competition threshold
            min_opportunity_score: Minimum opportunity score
            preferred_formats: Preferred video formats
            excluded_formats: Excluded video formats
            target_regions: Target region codes
            target_languages: Target language codes
            custom_settings: Additional custom settings
            is_template: Whether this is a read-only template
            created_by: Who created this niche
            change_reason: Reason for creating this niche

        Returns:
            Created niche configuration or None if failed
        """
        try:
            # Check if niche name already exists
            existing = self.get_by_name(niche_name)
            if existing:
                logger.warning("Niche '%s' already exists", niche_name)
                return None

            # Create niche
            niche = NicheConfig(
                niche_name=niche_name,
                display_name=display_name or niche_name,
                description=description,
                keywords=keywords,
                seed_topics=seed_topics,
                google_trends_enabled=1 if google_trends_enabled else 0,
                google_trends_weight=google_trends_weight,
                reddit_enabled=1 if reddit_enabled else 0,
                reddit_weight=reddit_weight,
                reddit_subreddits=reddit_subreddits,
                min_search_volume=min_search_volume,
                max_competition=max_competition,
                min_opportunity_score=min_opportunity_score,
                preferred_formats=preferred_formats,
                excluded_formats=excluded_formats,
                target_regions=target_regions,
                target_languages=target_languages,
                custom_settings=custom_settings,
                is_template=1 if is_template else 0,
                created_by=created_by,
                version=1,
                is_active=1
            )

            self.db.add(niche)
            self.db.flush()  # Get ID before creating history

            # Create history entry
            history = ConfigHistory.create_change(
                config_type='niche',
                config_id=niche.id,
                config_key=niche_name,
                change_type='create',
                changes={'niche_name': niche_name, 'keywords': keywords},
                new_value=self._niche_to_dict(niche),
                changed_by=created_by,
                change_reason=change_reason,
                rollback_data=self._niche_to_dict(niche)
            )

            self.db.add(history)
            self.db.commit()

            logger.info("Created niche '%s' (ID: %d)", niche_name, niche.id)
            return niche

        except Exception as e:
            logger.error("Failed to create niche '%s': %s", niche_name, str(e))
            self.db.rollback()
            return None

    def update(
        self,
        niche_id: int,
        changed_by: str = "user",
        change_reason: Optional[str] = None,
        **updates
    ) -> Optional[NicheConfig]:
        """Update a niche configuration.

        Args:
            niche_id: ID of niche to update
            changed_by: Who made the change
            change_reason: Reason for the change
            **updates: Fields to update

        Returns:
            Updated niche or None if failed
        """
        try:
            niche = self.get_by_id(niche_id)
            if not niche:
                logger.warning("Cannot update niche %d: not found", niche_id)
                return None

            # Don't allow updating templates
            if niche.is_template:
                logger.warning("Cannot update template niche '%s'", niche.niche_name)
                return None

            # Store old values for history
            old_values = self._niche_to_dict(niche)
            changes = {}

            # Update fields
            for key, value in updates.items():
                if hasattr(niche, key):
                    old_value = getattr(niche, key)
                    if old_value != value:
                        setattr(niche, key, value)
                        changes[key] = {'old': old_value, 'new': value}

            if not changes:
                logger.debug("No changes to apply for niche %d", niche_id)
                return niche

            # Increment version
            niche.version += 1
            niche.updated_at = datetime.utcnow()

            # Create history entry
            history = ConfigHistory.create_change(
                config_type='niche',
                config_id=niche.id,
                config_key=niche.niche_name,
                change_type='update',
                changes=changes,
                previous_value=old_values,
                new_value=self._niche_to_dict(niche),
                changed_by=changed_by,
                change_reason=change_reason,
                rollback_data=old_values
            )

            self.db.add(history)
            self.db.commit()

            logger.info("Updated niche '%s' (ID: %d, v%d)", niche.niche_name, niche.id, niche.version)
            return niche

        except Exception as e:
            logger.error("Failed to update niche %d: %s", niche_id, str(e))
            self.db.rollback()
            return None

    def delete(
        self,
        niche_id: int,
        changed_by: str = "user",
        change_reason: Optional[str] = None,
        hard_delete: bool = False
    ) -> bool:
        """Delete a niche configuration.

        Args:
            niche_id: ID of niche to delete
            changed_by: Who made the change
            change_reason: Reason for deletion
            hard_delete: If True, permanently delete. Otherwise, mark inactive.

        Returns:
            True if deleted successfully
        """
        try:
            niche = self.get_by_id(niche_id)
            if not niche:
                logger.warning("Cannot delete niche %d: not found", niche_id)
                return False

            # Don't allow deleting templates
            if niche.is_template:
                logger.warning("Cannot delete template niche '%s'", niche.niche_name)
                return False

            # Store old values for history
            old_values = self._niche_to_dict(niche)

            if hard_delete:
                # Permanently delete
                self.db.delete(niche)
            else:
                # Soft delete (mark inactive)
                niche.is_active = 0
                niche.updated_at = datetime.utcnow()

            # Create history entry
            history = ConfigHistory.create_change(
                config_type='niche',
                config_id=niche.id,
                config_key=niche.niche_name,
                change_type='delete',
                changes={'is_active': {'old': 1, 'new': 0}},
                previous_value=old_values,
                new_value=None if hard_delete else self._niche_to_dict(niche),
                changed_by=changed_by,
                change_reason=change_reason,
                rollback_data=old_values if not hard_delete else None
            )

            self.db.add(history)
            self.db.commit()

            logger.info("Deleted niche '%s' (ID: %d)", niche.niche_name, niche_id)
            return True

        except Exception as e:
            logger.error("Failed to delete niche %d: %s", niche_id, str(e))
            self.db.rollback()
            return False

    def duplicate(
        self,
        niche_id: int,
        new_name: str,
        created_by: str = "user",
        as_template: bool = False
    ) -> Optional[NicheConfig]:
        """Duplicate an existing niche configuration.

        Args:
            niche_id: ID of niche to duplicate
            new_name: Name for the new niche
            created_by: Who created the duplicate
            as_template: Whether to create as a template

        Returns:
            New niche configuration or None if failed
        """
        try:
            # Get source niche
            source = self.get_by_id(niche_id)
            if not source:
                logger.warning("Cannot duplicate niche %d: not found", niche_id)
                return None

            # Check if new name already exists
            if self.get_by_name(new_name):
                logger.warning("Cannot duplicate: niche '%s' already exists", new_name)
                return None

            # Create duplicate
            return self.create(
                niche_name=new_name,
                display_name=f"{source.display_name} (Copy)",
                description=source.description,
                keywords=source.keywords,
                seed_topics=source.seed_topics,
                google_trends_enabled=bool(source.google_trends_enabled),
                google_trends_weight=source.google_trends_weight,
                reddit_enabled=bool(source.reddit_enabled),
                reddit_weight=source.reddit_weight,
                reddit_subreddits=source.reddit_subreddits,
                min_search_volume=source.min_search_volume,
                max_competition=source.max_competition,
                min_opportunity_score=source.min_opportunity_score,
                preferred_formats=source.preferred_formats,
                excluded_formats=source.excluded_formats,
                target_regions=source.target_regions,
                target_languages=source.target_languages,
                custom_settings=source.custom_settings,
                is_template=as_template,
                created_by=created_by,
                change_reason=f"Duplicated from '{source.niche_name}'"
            )

        except Exception as e:
            logger.error("Failed to duplicate niche %d: %s", niche_id, str(e))
            return None

    def import_from_yaml(
        self,
        file_path: str,
        as_template: bool = True,
        created_by: str = "system"
    ) -> Optional[NicheConfig]:
        """Import a niche configuration from YAML file.

        Args:
            file_path: Path to YAML file
            as_template: Whether to import as template
            created_by: Who imported this niche

        Returns:
            Imported niche configuration or None if failed
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error("YAML file not found: %s", file_path)
                return None

            # Read and parse YAML
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # Calculate file hash
            file_hash = self._calculate_file_hash(path)

            # Extract niche name from filename or data
            niche_name = data.get('niche_name') or path.stem

            # Check if already imported
            existing = self.get_by_name(niche_name)
            if existing and existing.config_hash == file_hash:
                logger.info("Niche '%s' already imported with same content", niche_name)
                return existing

            # Create or update niche
            if existing:
                logger.info("Updating existing niche '%s' from YAML", niche_name)
                return self.update(
                    niche_id=existing.id,
                    changed_by=created_by,
                    change_reason=f"Imported from {path.name}",
                    **self._yaml_to_niche_fields(data, file_path, file_hash)
                )
            else:
                logger.info("Creating new niche '%s' from YAML", niche_name)
                return self.create(
                    niche_name=niche_name,
                    is_template=as_template,
                    created_by=created_by,
                    change_reason=f"Imported from {path.name}",
                    **self._yaml_to_niche_fields(data, file_path, file_hash)
                )

        except Exception as e:
            logger.error("Failed to import YAML from %s: %s", file_path, str(e))
            return None

    def export_to_yaml(self, niche_id: int, output_path: str) -> bool:
        """Export a niche configuration to YAML file.

        Args:
            niche_id: ID of niche to export
            output_path: Path to output YAML file

        Returns:
            True if exported successfully
        """
        try:
            niche = self.get_by_id(niche_id)
            if not niche:
                logger.warning("Cannot export niche %d: not found", niche_id)
                return False

            # Convert to YAML-friendly dict
            data = {
                'niche_name': niche.niche_name,
                'display_name': niche.display_name,
                'description': niche.description,
                'keywords': niche.keywords,
                'seed_topics': niche.seed_topics,
                'sources': {
                    'google_trends': {
                        'enabled': bool(niche.google_trends_enabled),
                        'weight': niche.google_trends_weight
                    },
                    'reddit': {
                        'enabled': bool(niche.reddit_enabled),
                        'weight': niche.reddit_weight,
                        'subreddits': niche.reddit_subreddits
                    }
                },
                'thresholds': {
                    'min_search_volume': niche.min_search_volume,
                    'max_competition': niche.max_competition,
                    'min_opportunity_score': niche.min_opportunity_score
                },
                'formats': {
                    'preferred': niche.preferred_formats,
                    'excluded': niche.excluded_formats
                },
                'regional': {
                    'target_regions': niche.target_regions,
                    'target_languages': niche.target_languages
                },
                'custom_settings': niche.custom_settings
            }

            # Write to YAML file
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

            logger.info("Exported niche '%s' to %s", niche.niche_name, output_path)
            return True

        except Exception as e:
            logger.error("Failed to export niche %d to YAML: %s", niche_id, str(e))
            return False

    def validate_config(self, niche_id: int) -> Dict[str, Any]:
        """Validate a niche configuration.

        Args:
            niche_id: ID of niche to validate

        Returns:
            Validation result with errors and warnings
        """
        niche = self.get_by_id(niche_id)
        if not niche:
            return {
                'valid': False,
                'errors': ['Niche not found'],
                'warnings': []
            }

        errors = []
        warnings = []

        # Validate keywords
        if not niche.keywords or len(niche.keywords) == 0:
            errors.append('No keywords defined')
        elif len(niche.keywords) < 3:
            warnings.append('Less than 3 keywords may limit discovery')

        # Validate sources
        if not niche.google_trends_enabled and not niche.reddit_enabled:
            errors.append('At least one source must be enabled')

        # Validate weights
        if niche.google_trends_enabled and not (0 <= niche.google_trends_weight <= 1):
            errors.append('Google Trends weight must be between 0 and 1')

        if niche.reddit_enabled and not (0 <= niche.reddit_weight <= 1):
            errors.append('Reddit weight must be between 0 and 1')

        # Validate Reddit subreddits
        if niche.reddit_enabled and (not niche.reddit_subreddits or len(niche.reddit_subreddits) == 0):
            warnings.append('Reddit enabled but no subreddits specified')

        # Validate thresholds
        if niche.min_search_volume and niche.min_search_volume < 0:
            errors.append('Minimum search volume cannot be negative')

        if niche.max_competition and not (0 <= niche.max_competition <= 1):
            errors.append('Maximum competition must be between 0 and 1')

        if niche.min_opportunity_score and not (0 <= niche.min_opportunity_score <= 100):
            errors.append('Minimum opportunity score must be between 0 and 100')

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'niche_name': niche.niche_name,
            'niche_id': niche.id
        }

    @staticmethod
    def _niche_to_dict(niche: NicheConfig) -> Dict[str, Any]:
        """Convert niche to dictionary.

        Args:
            niche: Niche configuration

        Returns:
            Dictionary representation
        """
        return {
            'id': niche.id,
            'niche_name': niche.niche_name,
            'display_name': niche.display_name,
            'description': niche.description,
            'keywords': niche.keywords,
            'seed_topics': niche.seed_topics,
            'google_trends_enabled': bool(niche.google_trends_enabled),
            'google_trends_weight': niche.google_trends_weight,
            'reddit_enabled': bool(niche.reddit_enabled),
            'reddit_weight': niche.reddit_weight,
            'reddit_subreddits': niche.reddit_subreddits,
            'min_search_volume': niche.min_search_volume,
            'max_competition': niche.max_competition,
            'min_opportunity_score': niche.min_opportunity_score,
            'preferred_formats': niche.preferred_formats,
            'excluded_formats': niche.excluded_formats,
            'target_regions': niche.target_regions,
            'target_languages': niche.target_languages,
            'custom_settings': niche.custom_settings,
            'is_template': bool(niche.is_template),
            'created_by': niche.created_by,
            'version': niche.version,
            'is_active': bool(niche.is_active)
        }

    @staticmethod
    def _yaml_to_niche_fields(data: Dict[str, Any], file_path: str, file_hash: str) -> Dict[str, Any]:
        """Convert YAML data to niche model fields.

        Args:
            data: YAML data dictionary
            file_path: Path to YAML file
            file_hash: SHA-256 hash of file content

        Returns:
            Dictionary of niche fields
        """
        sources = data.get('sources', {})
        google_trends = sources.get('google_trends', {})
        reddit = sources.get('reddit', {})
        thresholds = data.get('thresholds', {})
        formats = data.get('formats', {})
        regional = data.get('regional', {})

        return {
            'display_name': data.get('display_name'),
            'description': data.get('description'),
            'keywords': data.get('keywords', []),
            'seed_topics': data.get('seed_topics'),
            'google_trends_enabled': google_trends.get('enabled', True),
            'google_trends_weight': google_trends.get('weight', 0.5),
            'reddit_enabled': reddit.get('enabled', True),
            'reddit_weight': reddit.get('weight', 0.5),
            'reddit_subreddits': reddit.get('subreddits'),
            'min_search_volume': thresholds.get('min_search_volume'),
            'max_competition': thresholds.get('max_competition'),
            'min_opportunity_score': thresholds.get('min_opportunity_score'),
            'preferred_formats': formats.get('preferred'),
            'excluded_formats': formats.get('excluded'),
            'target_regions': regional.get('target_regions'),
            'target_languages': regional.get('target_languages'),
            'custom_settings': data.get('custom_settings'),
            'config_file_path': file_path,
            'config_hash': file_hash
        }

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA-256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            SHA-256 hash as hex string
        """
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
