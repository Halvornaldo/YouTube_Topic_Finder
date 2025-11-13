#!/usr/bin/env python3
"""Add Robot 1.5 (Topic Scorer) configuration settings to database."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.database import get_db
from src.models.app_setting import AppSetting

print("=== Adding Robot 1.5 Configuration Settings ===\n")

db = next(get_db())
try:
    # Settings to add
    settings_data = [
        {
            "key": "robot1_5_batch_size",
            "value": "20",
            "data_type": "int",
            "category": "robot1_5",
            "description": "Number of topics to score per run",
            "default_value": "20",
            "requires_restart": False,
            "is_active": True
        },
        {
            "key": "robot1_5_llm_weight",
            "value": "0.7",
            "data_type": "float",
            "category": "robot1_5",
            "description": "Weight of LLM score in final score (0.0-1.0). Default 0.7 means 70% LLM, 30% raw",
            "default_value": "0.7",
            "requires_restart": False,
            "is_active": True
        },
        {
            "key": "robot1_5_min_llm_score",
            "value": "60.0",
            "data_type": "float",
            "category": "robot1_5",
            "description": "Minimum LLM score to accept a topic (0-100). Topics below this are rejected",
            "default_value": "60.0",
            "requires_restart": False,
            "is_active": True
        }
    ]

    for setting_data in settings_data:
        # Check if setting already exists
        existing = db.query(AppSetting).filter(
            AppSetting.key == setting_data["key"]
        ).first()

        if existing:
            print(f"[SKIP] {setting_data['key']} - already exists")
        else:
            # Create new setting using ORM
            setting = AppSetting(**setting_data)
            db.add(setting)
            print(f"[OK] Added {setting_data['key']} = {setting_data['value']}")

    db.commit()
    print("\n=== Configuration Settings Added ===")
    print("\nRobot 1.5 is now configured with:")
    print("- batch_size: 20 topics per run")
    print("- llm_weight: 0.7 (70% LLM score, 30% raw score)")
    print("- min_llm_score: 60.0 (topics below 60 are rejected)")
    print("\nYou can adjust these values via the settings API:")
    print("  PUT /api/settings/{key}")

finally:
    db.close()
