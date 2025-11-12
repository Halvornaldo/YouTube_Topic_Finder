#!/usr/bin/env python3
"""
Initialize Robot 3 (Metric Analyzer) settings in the database.

This script populates the app_settings table with default configuration
for Robot 3, following the same pattern as Robot 1 and Robot 2.

Usage:
    python scripts/init_robot3_settings.py
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


def init_robot3_settings(db: Session) -> int:
    """
    Initialize Robot 3 (Metric Analyzer) settings.

    Args:
        db: Database session

    Returns:
        Number of settings created
    """
    robot3_settings = [
        # General Robot 3 Settings
        {
            'key': 'robot3.batch_size',
            'value': '50',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Maximum number of videos to process per run',
            'default_value': '50',
            'is_active': True
        },
        {
            'key': 'robot3.youtube_api_enabled',
            'value': 'true',
            'category': 'robot3',
            'data_type': 'boolean',
            'requires_restart': False,
            'description': 'Enable YouTube Data API v3 for fetching video metrics',
            'default_value': 'true',
            'is_active': True
        },
        {
            'key': 'robot3.google_ads_enabled',
            'value': 'false',
            'category': 'robot3',
            'data_type': 'boolean',
            'requires_restart': False,
            'description': 'Enable Google Ads API for search volume data (requires API setup)',
            'default_value': 'false',
            'is_active': True
        },
        {
            'key': 'robot3.max_videos_per_run',
            'value': '500',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Maximum number of videos to process in a single run (safety limit)',
            'default_value': '500',
            'is_active': True
        },
        {
            'key': 'robot3.delay_between_videos',
            'value': '0.5',
            'category': 'robot3',
            'data_type': 'float',
            'requires_restart': False,
            'description': 'Delay in seconds between processing videos (rate limiting)',
            'default_value': '0.5',
            'is_active': True
        },
        {
            'key': 'robot3.skip_on_api_error',
            'value': 'true',
            'category': 'robot3',
            'data_type': 'boolean',
            'requires_restart': False,
            'description': 'Skip videos that fail API calls (continue processing) instead of failing entire job',
            'default_value': 'true',
            'is_active': True
        },

        # Opportunity Score Weights (must sum to 100)
        {
            'key': 'robot3.weight_search_volume',
            'value': '25',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Weight for search volume score in overall opportunity score (0-100)',
            'default_value': '25',
            'is_active': True
        },
        {
            'key': 'robot3.weight_competition',
            'value': '20',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Weight for competition score in overall opportunity score (0-100)',
            'default_value': '20',
            'is_active': True
        },
        {
            'key': 'robot3.weight_velocity',
            'value': '20',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Weight for velocity score in overall opportunity score (0-100)',
            'default_value': '20',
            'is_active': True
        },
        {
            'key': 'robot3.weight_engagement',
            'value': '20',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Weight for engagement score in overall opportunity score (0-100)',
            'default_value': '20',
            'is_active': True
        },
        {
            'key': 'robot3.weight_sentiment',
            'value': '0',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Weight for sentiment score in overall opportunity score (0-100, currently disabled)',
            'default_value': '0',
            'is_active': True
        },
        {
            'key': 'robot3.weight_recency',
            'value': '15',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Weight for recency score in overall opportunity score (0-100)',
            'default_value': '15',
            'is_active': True
        },

        # Competition Thresholds
        {
            'key': 'robot3.competition_low_threshold',
            'value': '10',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Maximum competing videos for LOW competition level',
            'default_value': '10',
            'is_active': True
        },
        {
            'key': 'robot3.competition_medium_threshold',
            'value': '50',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Maximum competing videos for MEDIUM competition level (10-50)',
            'default_value': '50',
            'is_active': True
        },
        {
            'key': 'robot3.competition_high_threshold',
            'value': '200',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Maximum competing videos for HIGH competition level (50-200, >200 is VERY_HIGH)',
            'default_value': '200',
            'is_active': True
        },

        # Recommendation Criteria
        {
            'key': 'robot3.min_opportunity_score',
            'value': '70',
            'category': 'robot3',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Minimum opportunity score to mark as recommended (0-100)',
            'default_value': '70',
            'is_active': True
        },
        {
            'key': 'robot3.min_confidence_score',
            'value': '0.7',
            'category': 'robot3',
            'data_type': 'float',
            'requires_restart': False,
            'description': 'Minimum confidence score for trend predictions (0-1)',
            'default_value': '0.7',
            'is_active': True
        }
    ]

    created_count = 0
    updated_count = 0

    for setting_data in robot3_settings:
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
    logger.info(f"Robot 3 settings initialized: {created_count} created, {updated_count} already existed")

    return created_count


def init_google_ads_api_settings(db: Session) -> int:
    """
    Initialize Google Ads API settings (empty, user must configure).

    Args:
        db: Database session

    Returns:
        Number of settings created
    """
    google_ads_settings = [
        {
            'key': 'google_ads.developer_token',
            'value': '',
            'category': 'api_keys',
            'data_type': 'string',
            'requires_restart': False,
            'description': 'Google Ads API developer token. Apply at: https://developers.google.com/google-ads/api/docs/first-call/dev-token',
            'default_value': '',
            'is_active': True
        },
        {
            'key': 'google_ads.client_id',
            'value': '',
            'category': 'api_keys',
            'data_type': 'string',
            'requires_restart': False,
            'description': 'Google Ads API OAuth2 client ID',
            'default_value': '',
            'is_active': True
        },
        {
            'key': 'google_ads.client_secret',
            'value': '',
            'category': 'api_keys',
            'data_type': 'string',
            'requires_restart': False,
            'description': 'Google Ads API OAuth2 client secret',
            'default_value': '',
            'is_active': True
        },
        {
            'key': 'google_ads.refresh_token',
            'value': '',
            'category': 'api_keys',
            'data_type': 'string',
            'requires_restart': False,
            'description': 'Google Ads API OAuth2 refresh token',
            'default_value': '',
            'is_active': True
        },
        {
            'key': 'google_ads.customer_id',
            'value': '',
            'category': 'api_keys',
            'data_type': 'string',
            'requires_restart': False,
            'description': 'Google Ads customer/account ID (without dashes)',
            'default_value': '',
            'is_active': True
        }
    ]

    created_count = 0

    for setting_data in google_ads_settings:
        # Check if setting already exists
        existing_setting = db.query(AppSetting).filter(
            AppSetting.key == setting_data['key']
        ).first()

        if existing_setting:
            logger.info(f"API key setting already exists: {setting_data['key']} (skipping)")
        else:
            setting = AppSetting(**setting_data)
            db.add(setting)
            created_count += 1
            logger.info(f"Created API key setting: {setting_data['key']} (empty - user must configure)")

    if created_count > 0:
        db.commit()

    return created_count


def init_youtube_quota_settings(db: Session) -> int:
    """
    Initialize YouTube API quota management settings.

    Args:
        db: Database session

    Returns:
        Number of settings created
    """
    quota_settings = [
        {
            'key': 'youtube.daily_quota_limit',
            'value': '10000',
            'category': 'api_keys',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'YouTube Data API v3 daily quota limit (default: 10,000 units/day)',
            'default_value': '10000',
            'is_active': True
        },
        {
            'key': 'youtube.quota_reset_hour',
            'value': '0',
            'category': 'api_keys',
            'data_type': 'integer',
            'requires_restart': False,
            'description': 'Hour of day when YouTube API quota resets (UTC, 0-23)',
            'default_value': '0',
            'is_active': True
        }
    ]

    created_count = 0

    for setting_data in quota_settings:
        # Check if setting already exists
        existing_setting = db.query(AppSetting).filter(
            AppSetting.key == setting_data['key']
        ).first()

        if existing_setting:
            logger.info(f"Quota setting already exists: {setting_data['key']} (skipping)")
        else:
            setting = AppSetting(**setting_data)
            db.add(setting)
            created_count += 1
            logger.info(f"Created quota setting: {setting_data['key']}")

    if created_count > 0:
        db.commit()

    return created_count


def main():
    """Main entry point for settings initialization."""
    logger.info("=" * 60)
    logger.info("Robot 3 Settings Initialization")
    logger.info("=" * 60)

    # Get database session
    db = next(get_db())

    try:
        # Initialize Robot 3 settings
        robot3_count = init_robot3_settings(db)

        # Initialize Google Ads API settings
        google_ads_count = init_google_ads_api_settings(db)

        # Initialize YouTube quota settings
        youtube_quota_count = init_youtube_quota_settings(db)

        total_created = robot3_count + google_ads_count + youtube_quota_count

        logger.info("=" * 60)
        logger.info(f"Initialization complete! {total_created} settings created.")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. [REQUIRED] Ensure YouTube API key is configured: youtube.api_key")
        logger.info("   (Should already be set from Robot 2)")
        logger.info("")
        logger.info("2. [OPTIONAL] Configure Google Ads API for search volume data:")
        logger.info("   - google_ads.developer_token")
        logger.info("   - google_ads.client_id")
        logger.info("   - google_ads.client_secret")
        logger.info("   - google_ads.refresh_token")
        logger.info("   - google_ads.customer_id")
        logger.info("   Setup guide: https://developers.google.com/google-ads/api/docs/first-call/overview")
        logger.info("")
        logger.info("3. [OPTIONAL] Adjust scoring weights (must sum to 100):")
        logger.info("   - robot3.weight_search_volume (default: 25)")
        logger.info("   - robot3.weight_competition (default: 20)")
        logger.info("   - robot3.weight_velocity (default: 20)")
        logger.info("   - robot3.weight_engagement (default: 20)")
        logger.info("   - robot3.weight_sentiment (default: 0 - not implemented)")
        logger.info("   - robot3.weight_recency (default: 15)")
        logger.info("")
        logger.info("4. Test Robot 3: POST /api/robots/metric-analyzer/run")
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
