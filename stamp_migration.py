#!/usr/bin/env python3
"""Stamp the database as being at a specific migration version."""

import os
import sys
from src.config.settings import settings

# Set DATABASE_URL environment variable from settings
os.environ['DATABASE_URL'] = settings.DATABASE_URL

print(f"Using DATABASE_URL: {settings.DATABASE_URL[:50]}...")
print("Stamping database to mark initial migration as applied...")

# Run alembic stamp with the initial migration ID
import subprocess
result = subprocess.run([sys.executable, '-m', 'alembic', 'stamp', '51def9469a47'])
sys.exit(result.returncode)
