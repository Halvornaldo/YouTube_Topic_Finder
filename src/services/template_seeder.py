"""Template seeding service for loading YAML niche configurations into database."""

import logging
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.models.niche_config import NicheConfig
from src.config.settings import settings

logger = logging.getLogger(__name__)


class TemplateSeeder:
    """
    Service for loading YAML template configurations into the database.

    Reads niche configuration YAML files from the templates directory and
    creates corresponding database records marked as templates.
    """

    def __init__(self, db_session: Session, templates_dir: Optional[str] = None):
        """
        Initialize template seeder.

        Args:
            db_session: Database session
            templates_dir: Directory containing YAML templates
        """
        self.db = db_session
        self.templates_dir = Path(templates_dir or settings.CONFIG_DIR)

    def seed_all_templates(self, overwrite: bool = False) -> Dict:
        """
        Seed all YAML templates into the database.

        Args:
            overwrite: If True, update existing templates. If False, skip existing.

        Returns:
            Dict with seeding results
        """
        logger.info(f"Starting template seeding from {self.templates_dir}")

        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {self.templates_dir}")

        results = {
            'total_files': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }

        # Find all YAML files
        yaml_files = list(self.templates_dir.glob("**/*.yaml")) + list(self.templates_dir.glob("**/*.yml"))

        results['total_files'] = len(yaml_files)

        for yaml_file in yaml_files:
            try:
                result = self.seed_template(yaml_file, overwrite=overwrite)

                if result == 'created':
                    results['created'] += 1
                elif result == 'updated':
                    results['updated'] += 1
                elif result == 'skipped':
                    results['skipped'] += 1

            except Exception as e:
                logger.error(f"Error seeding template {yaml_file}: {e}", exc_info=True)
                results['errors'].append({
                    'file': str(yaml_file),
                    'error': str(e)
                })

        # Commit all changes
        try:
            self.db.commit()
            logger.info(f"Template seeding completed: {results}")
        except Exception as e:
            logger.error(f"Error committing templates: {e}")
            self.db.rollback()
            raise

        return results

    def seed_template(self, yaml_file: Path, overwrite: bool = False) -> str:
        """
        Seed a single YAML template into the database.

        Args:
            yaml_file: Path to YAML file
            overwrite: If True, update existing template

        Returns:
            Status: 'created', 'updated', or 'skipped'
        """
        # Load YAML file
        with open(yaml_file, 'r') as f:
            config_data = yaml.safe_load(f)

        # Extract configuration fields
        name = config_data.get('name')
        if not name:
            raise ValueError(f"Template {yaml_file} missing required 'name' field")

        # Check if template already exists
        stmt = select(NicheConfig).where(
            NicheConfig.niche_name == name,
            NicheConfig.is_template == 1
        )
        existing = self.db.execute(stmt).scalar_one_or_none()

        if existing and not overwrite:
            logger.debug(f"Template '{name}' already exists, skipping")
            return 'skipped'

        # Parse source configuration
        sources = config_data.get('sources', {})
        google_trends = sources.get('google_trends', {})
        reddit = sources.get('reddit', {})

        # Parse thresholds
        thresholds = config_data.get('thresholds', {})

        # Parse formats
        formats = config_data.get('formats', {})

        # Prepare niche config data
        niche_data = {
            'niche_name': name,
            'description': config_data.get('description', ''),
            'keywords': config_data.get('keywords', []),
            'seed_topics': config_data.get('seed_topics', []),
            'google_trends_weight': google_trends.get('weight', 0.5),
            'reddit_weight': reddit.get('weight', 0.5),
            'min_search_volume': thresholds.get('min_search_volume', 1000),
            'max_competition': thresholds.get('max_competition', 0.7),
            'min_opportunity_score': thresholds.get('min_opportunity_score', 60.0),
            'preferred_formats': formats.get('preferred', []),
            'is_template': 1,  # Mark as template
            'is_active': 1,
            'created_by': 'system'
        }

        if existing:
            # Update existing template
            for key, value in niche_data.items():
                setattr(existing, key, value)

            logger.info(f"Updated template: {name}")
            return 'updated'
        else:
            # Create new template
            niche_config = NicheConfig(**niche_data)
            self.db.add(niche_config)

            logger.info(f"Created template: {name}")
            return 'created'

    def clear_templates(self) -> int:
        """
        Remove all template niche configurations from the database.

        Returns:
            Number of templates deleted
        """
        stmt = select(NicheConfig).where(NicheConfig.is_template == 1)
        templates = self.db.execute(stmt).scalars().all()

        count = len(templates)

        for template in templates:
            self.db.delete(template)

        self.db.commit()

        logger.info(f"Cleared {count} templates from database")
        return count

    def get_template_count(self) -> int:
        """
        Get count of template niche configurations in database.

        Returns:
            Number of templates
        """
        from sqlalchemy import func

        count = self.db.execute(
            select(func.count()).select_from(NicheConfig).where(
                NicheConfig.is_template == 1
            )
        ).scalar()

        return count

    def list_template_files(self) -> List[Path]:
        """
        List all YAML template files in the templates directory.

        Returns:
            List of YAML file paths
        """
        if not self.templates_dir.exists():
            return []

        yaml_files = list(self.templates_dir.glob("**/*.yaml")) + list(self.templates_dir.glob("**/*.yml"))
        return sorted(yaml_files)

    def validate_templates(self) -> Dict:
        """
        Validate all YAML template files without importing them.

        Returns:
            Dict with validation results
        """
        results = {
            'valid_files': [],
            'invalid_files': [],
            'total': 0
        }

        yaml_files = self.list_template_files()
        results['total'] = len(yaml_files)

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r') as f:
                    config_data = yaml.safe_load(f)

                # Check required fields
                required_fields = ['name', 'keywords']
                missing_fields = [f for f in required_fields if f not in config_data]

                if missing_fields:
                    results['invalid_files'].append({
                        'file': str(yaml_file),
                        'error': f"Missing required fields: {', '.join(missing_fields)}"
                    })
                else:
                    results['valid_files'].append(str(yaml_file))

            except Exception as e:
                results['invalid_files'].append({
                    'file': str(yaml_file),
                    'error': str(e)
                })

        return results


def seed_default_templates(db: Session, overwrite: bool = False) -> Dict:
    """
    Convenience function to seed default templates.

    Args:
        db: Database session
        overwrite: Whether to overwrite existing templates

    Returns:
        Seeding results
    """
    seeder = TemplateSeeder(db)
    return seeder.seed_all_templates(overwrite=overwrite)
