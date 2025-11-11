#!/usr/bin/env python3
"""Run Alembic migrations with DATABASE_URL from settings."""

import os
import sys
from src.config.settings import settings

# Set DATABASE_URL environment variable from settings
os.environ['DATABASE_URL'] = settings.DATABASE_URL

print(f"Using DATABASE_URL: {settings.DATABASE_URL[:50]}...")

# Run alembic upgrade head
import subprocess
result = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'])
sys.exit(result.returncode)
