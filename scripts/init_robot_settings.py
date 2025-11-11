#!/usr/bin/env python3
"""
Initialize Robot 2 (SERP Scraper) settings in the database.

This script populates the app_settings table with default configuration
for Robot 2, following the same pattern as Robot 1.

Usage:
    python scripts/init_robot_settings.py
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from src.config.database import get_db
from src.models.app_setting import AppSetting
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_robot2_settings(db: Session) -> int:
    """
    Initialize Robot 2 (SERP Scraper) settings.

    Args:
        db: Database session

    Returns:
        Number of settings created
    """
    robot2_settings = [
        {
            'key': 'robot2.use_playwright',
            'value': 'false',  # Default to false due to Windows/Python 3.13 compatibility issues
            'category': 'robot2',
            'data_type': 'boolean',
            'requires_restart': False,
            'description': 'Enable Playwright browser automation for YouTube scraping. Set to false if experiencing compatibility issues (Windows/Python 3.13).',
            'default_value': 'false',
            'is_active': True
        },
        {
            'key': 'robot2.headless',
            'value': 'true',
            'category': 'robot2',
            'data_type': 'boolean',
            'requires_restart': False,
            'description': 'Run Playwright browser in headless mode (no visible window)',
            'default_value': 'true',
            'is_active': True
        },
        {
            'key': 'robot2.youtube_api_fallback',
            'value': 'true',
            'category': 'robot2',
            'data_type': 'boolean',
            'requires_restart': False,
            'description': 'Use YouTube Data API v3 as fallback when Playwright fails or is disabled',
            'default_value': 'true',
            'is_active': True
        },
        {
            'key': 'robot2.delay_between_searches',
            'value': '3',
            'category': 'robot2',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Delay in seconds between YouTube searches (rate limiting)',
            'default_value': '3',
            'is_active': True
        },
        {
            'key': 'robot2.max_topics_per_run',
            'value': '10',
            'category': 'robot2',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Maximum number of seed topics to process per run',
            'default_value': '10',
            'is_active': True
        },
        {
            'key': 'robot2.max_videos_per_query',
            'value': '20',
            'category': 'robot2',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Maximum number of videos to scrape per search query',
            'default_value': '20',
            'is_active': True
        },
        {
            'key': 'robot2.screenshot_on_error',
            'value': 'false',
            'category': 'robot2',
            'data_type': 'boolean',
            'requires_restart': False,
            'description': 'Capture screenshot when Playwright encounters errors (for debugging)',
            'default_value': 'false',
            'is_active': True
        },
        {
            'key': 'robot2.user_agent',
            'value': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'category': 'robot2',
            'data_type': 'string',
            'requires_restart': False,
            'description': 'Custom User-Agent string for Playwright browser',
            'default_value': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'is_active': True
        }
    ]

    created_count = 0
    updated_count = 0

    for setting_data in robot2_settings:
        # Check if setting already exists
        existing_setting = db.query(AppSetting).filter(
            AppSetting.key == setting_data['key']
        ).first()

        if existing_setting:
            logger.info(f"Setting already exists: {setting_data['key']} (skipping)")
            updated_count += 1
        else:
            # Create new setting
            setting = AppSetting(**setting_data)
            db.add(setting)
            created_count += 1
            logger.info(f"Created setting: {setting_data['key']}")

    db.commit()
    logger.info(f"Robot 2 settings initialized: {created_count} created, {updated_count} already existed")

    return created_count


def init_youtube_api_key(db: Session) -> int:
    """
    Initialize YouTube API key setting (empty, user must configure).

    Args:
        db: Database session

    Returns:
        Number of settings created
    """
    api_key_setting = {
        'key': 'youtube.api_key',
        'value': '',  # Empty - user must configure
        'category': 'api_keys',
        'data_type': 'string',
        'requires_restart': False,
        'description': 'YouTube Data API v3 key for video metadata retrieval. Get from: https://console.cloud.google.com/apis/credentials',
        'default_value': '',
        'is_active': True
    }

    # Check if setting already exists
    existing_setting = db.query(AppSetting).filter(
        AppSetting.key == api_key_setting['key']
    ).first()

    if existing_setting:
        logger.info(f"API key setting already exists: {api_key_setting['key']} (skipping)")
        return 0
    else:
        setting = AppSetting(**api_key_setting)
        db.add(setting)
        db.commit()
        logger.info(f"Created API key setting: {api_key_setting['key']} (empty - user must configure)")
        return 1


def main():
    """Main entry point for settings initialization."""
    logger.info("=" * 60)
    logger.info("Robot 2 Settings Initialization")
    logger.info("=" * 60)

    # Get database session
    db = next(get_db())

    try:
        # Initialize Robot 2 settings
        robot2_count = init_robot2_settings(db)

        # Initialize YouTube API key
        api_key_count = init_youtube_api_key(db)

        total_created = robot2_count + api_key_count

        logger.info("=" * 60)
        logger.info(f"Initialization complete! {total_created} settings created.")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Configure YouTube API key: youtube.api_key")
        logger.info("   Get API key from: https://console.cloud.google.com/apis/credentials")
        logger.info("2. Adjust Robot 2 settings as needed via settings API")
        logger.info("3. Test Robot 2: POST /api/robots/serp-scraper/run")
        logger.info("")

        return 0

    except Exception as e:
        logger.error(f"Error initializing settings: {e}", exc_info=True)
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(main())
