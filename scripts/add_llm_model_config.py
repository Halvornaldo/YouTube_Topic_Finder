"""Add LLM model configuration for Robot 1.5."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.database import SessionLocal
from src.models.app_setting import AppSetting

def add_llm_model_config():
    """Add robot1_5_llm_model setting to database."""
    db = SessionLocal()

    try:
        print("=== Adding Robot 1.5 LLM Model Configuration ===\n")

        # Check if setting already exists
        existing = db.query(AppSetting).filter(
            AppSetting.key == "robot1_5_llm_model"
        ).first()

        if existing:
            print(f"[SKIP] robot1_5_llm_model already exists: {existing.value}")
            print(f"       To change it, use: PUT /api/settings/robot1_5_llm_model")
            return

        # Add new setting
        setting = AppSetting(
            key="robot1_5_llm_model",
            value="gemini-2.0-flash-exp",
            category="robot_config",
            data_type="string",
            description="Gemini model for Robot 1.5 topic scoring. Options: gemini-2.0-flash-exp (fastest/cheapest), gemini-1.5-flash (production stable), gemini-1.5-pro (highest quality)",
            requires_restart=False  # Hot-reloadable!
        )

        db.add(setting)
        db.commit()

        print("[ADDED] robot1_5_llm_model")
        print(f"        Value: {setting.value}")
        print(f"        Hot-reloadable: {not setting.requires_restart}")
        print(f"        Category: {setting.category}")

        print("\n=== LLM Model Configuration Added ===")
        print("\nAvailable models:")
        print("  - gemini-2.0-flash-exp (default) - Experimental, fastest, cheapest")
        print("  - gemini-1.5-flash - Production stable, fast")
        print("  - gemini-1.5-pro - Highest quality, slower, expensive")
        print("  - gemini-1.0-pro - Legacy, not recommended")

        print("\nTo change model without restart:")
        print('  curl -X PUT http://localhost:8000/api/settings/robot1_5_llm_model \\')
        print('    -H "Content-Type: application/json" \\')
        print('    -d \'{"value": "gemini-1.5-flash"}\'')

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to add setting: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    add_llm_model_config()
