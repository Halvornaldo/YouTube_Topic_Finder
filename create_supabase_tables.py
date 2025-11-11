#!/usr/bin/env python3
"""Create tables in Supabase database."""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
load_dotenv()

from src.models.base import Base
from src.models.seed_topic import SeedTopic
from src.models.video import Video
from src.models.video_metric import VideoMetric
from src.models.opportunity_score import OpportunityScore
from src.models.video_format import VideoFormat
from src.models.search_query import SearchQuery
from src.models.content_gap import ContentGap
from src.models.niche_config import NicheConfig
from src.models.processing_job import ProcessingJob
from src.models.app_setting import AppSetting
from src.models.job_status import JobStatus
from src.models.config_history import ConfigHistory

from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError

def main():
    """Create all tables in Supabase."""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not found in environment")
        sys.exit(1)

    print(f"Connecting to Supabase...")
    print(f"Database: {database_url.split('@')[1].split('/')[0]}")  # Hide password

    # Create engine
    engine = create_engine(database_url)

    try:
        # Create all tables
        print("\nCreating tables...")
        Base.metadata.create_all(bind=engine)
        print("[SUCCESS] All tables created successfully!")

        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")

    except Exception as e:
        print(f"[ERROR] Error creating tables: {e}")
        sys.exit(1)
    finally:
        engine.dispose()

    print("\n[COMPLETE] Supabase database setup complete!")
    print("You can view your tables at: https://supabase.com/dashboard/project/etaacgjaghqoorbrfqzh/editor")

if __name__ == "__main__":
    main()