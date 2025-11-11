#!/usr/bin/env python3
"""Run template seeding with DATABASE_URL from settings."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import settings

# Set DATABASE_URL environment variable from settings
os.environ['DATABASE_URL'] = settings.DATABASE_URL

print(f"Using DATABASE_URL: {settings.DATABASE_URL[:50]}...")

# Now import and run the seeding script
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.services.template_seeder import TemplateSeeder

# Create database session
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Initialize seeder
    seeder = TemplateSeeder(db)

    # Seed templates
    print("\nSeeding YAML templates...")
    results = seeder.seed_all_templates(overwrite=False)

    # Print results
    print("\n" + "=" * 60)
    print("TEMPLATE SEEDING RESULTS")
    print("=" * 60)
    print(f"\nTotal YAML files found: {results['total_files']}")
    print(f"Created:  {results['created']}")
    print(f"Updated:  {results['updated']}")
    print(f"Skipped:  {results['skipped']}")

    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  - {error['file']}")
            print(f"    {error['error']}")

    print("\n" + "=" * 60)
    print(f"Database seeding completed!")
    print("=" * 60 + "\n")

    # Get final count
    template_count = seeder.get_template_count()
    print(f"Total templates in database: {template_count}\n")

except Exception as e:
    print(f"\nError: {e}\n")
    sys.exit(1)

finally:
    db.close()
