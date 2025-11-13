#!/usr/bin/env python3
"""Apply GDELT migration to Supabase database."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.config.database import get_db

print("Applying GDELT migration to niche_configs table...")

db = next(get_db())
try:
    # Check if columns already exist
    result = db.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'niche_configs'
        AND column_name IN ('gdelt_enabled', 'gdelt_weight')
    """))

    existing_columns = [row[0] for row in result.fetchall()]

    if 'gdelt_enabled' in existing_columns and 'gdelt_weight' in existing_columns:
        print("[OK] GDELT columns already exist in niche_configs table")
    else:
        # Add gdelt_enabled column if it doesn't exist
        if 'gdelt_enabled' not in existing_columns:
            print("Adding gdelt_enabled column...")
            db.execute(text("""
                ALTER TABLE niche_configs
                ADD COLUMN gdelt_enabled INTEGER DEFAULT 1
            """))
            print("[OK] Added gdelt_enabled column")

        # Add gdelt_weight column if it doesn't exist
        if 'gdelt_weight' not in existing_columns:
            print("Adding gdelt_weight column...")
            db.execute(text("""
                ALTER TABLE niche_configs
                ADD COLUMN gdelt_weight FLOAT DEFAULT 0.5
            """))
            print("[OK] Added gdelt_weight column")

        # Update existing rows to have the default values
        print("Updating existing rows with default values...")
        db.execute(text("""
            UPDATE niche_configs
            SET gdelt_enabled = 1
            WHERE gdelt_enabled IS NULL
        """))
        db.execute(text("""
            UPDATE niche_configs
            SET gdelt_weight = 0.5
            WHERE gdelt_weight IS NULL
        """))

        db.commit()
        print("[OK] Migration applied successfully")

    # Show updated schema
    print("\nVerifying niche_configs columns:")
    result = db.execute(text("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'niche_configs'
        AND column_name LIKE '%gdelt%'
        ORDER BY column_name
    """))

    for row in result.fetchall():
        print(f"  - {row[0]}: {row[1]} (default: {row[2]})")

finally:
    db.close()

print("\n[SUCCESS] GDELT migration complete!")
