#!/usr/bin/env python3
"""Standalone script to seed YAML templates into the database."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.services.template_seeder import TemplateSeeder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for template seeding script."""
    parser = argparse.ArgumentParser(
        description='Seed YAML niche templates into the database'
    )

    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing templates (default: skip existing)'
    )

    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear all existing templates before seeding'
    )

    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate YAML files without importing'
    )

    parser.add_argument(
        '--templates-dir',
        type=str,
        default=None,
        help=f'Templates directory (default: {settings.CONFIG_DIR})'
    )

    args = parser.parse_args()

    # Create database session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Initialize seeder
        seeder = TemplateSeeder(db, templates_dir=args.templates_dir)

        if args.validate_only:
            # Validate templates only
            logger.info("Validating YAML template files...")
            results = seeder.validate_templates()

            print("\n" + "=" * 60)
            print(f"VALIDATION RESULTS ({results['total']} files)")
            print("=" * 60)

            if results['valid_files']:
                print(f"\n✓ Valid files ({len(results['valid_files'])}):")
                for file in results['valid_files']:
                    print(f"  - {file}")

            if results['invalid_files']:
                print(f"\n✗ Invalid files ({len(results['invalid_files'])}):")
                for item in results['invalid_files']:
                    print(f"  - {item['file']}")
                    print(f"    Error: {item['error']}")

            sys.exit(0 if not results['invalid_files'] else 1)

        if args.clear:
            # Clear existing templates
            logger.info("Clearing existing templates...")
            count = seeder.clear_templates()
            print(f"\n✓ Cleared {count} existing templates")

        # Seed templates
        logger.info("Seeding templates...")
        results = seeder.seed_all_templates(overwrite=args.overwrite)

        # Print results
        print("\n" + "=" * 60)
        print("TEMPLATE SEEDING RESULTS")
        print("=" * 60)
        print(f"\nTotal YAML files found: {results['total_files']}")
        print(f"✓ Created:  {results['created']}")
        print(f"↻ Updated:  {results['updated']}")
        print(f"- Skipped:  {results['skipped']}")

        if results['errors']:
            print(f"\n✗ Errors ({len(results['errors'])}):")
            for error in results['errors']:
                print(f"  - {error['file']}")
                print(f"    {error['error']}")

        print("\n" + "=" * 60)
        print(f"✓ Database seeding completed successfully!")
        print("=" * 60 + "\n")

        # Get final count
        template_count = seeder.get_template_count()
        print(f"Total templates in database: {template_count}\n")

    except Exception as e:
        logger.error(f"Error during template seeding: {e}", exc_info=True)
        print(f"\n✗ Error: {e}\n")
        sys.exit(1)

    finally:
        db.close()


if __name__ == '__main__':
    main()
