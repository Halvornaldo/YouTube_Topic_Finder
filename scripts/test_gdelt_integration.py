#!/usr/bin/env python3
"""Test GDELT integration for Robot 1."""

import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from src.config.database import get_db
from src.robots.horizon_scanner import HorizonScanner
from sqlalchemy import text

print("=== Testing GDELT Integration ===\n")

# Test 1: GDELT API Connectivity
print("Test 1: Testing GDELT API connectivity...")
try:
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        'query': 'artificial intelligence',
        'mode': 'artlist',
        'maxrecords': 5,
        'format': 'json',
        'timespan': '3d',
        'sort': 'hybridrel'
    }

    response = requests.get(base_url, params=params, timeout=15)

    if response.status_code == 200:
        data = response.json()
        articles = data.get('articles', [])
        print(f"[OK] GDELT API accessible - Found {len(articles)} articles")

        if articles:
            print("\nSample article:")
            article = articles[0]
            # Use ASCII encoding to avoid Windows terminal encoding issues
            title = article.get('title', 'N/A')[:80].encode('ascii', 'ignore').decode('ascii')
            url = article.get('url', 'N/A')[:80].encode('ascii', 'ignore').decode('ascii')
            domain = article.get('domain', 'N/A')
            print(f"  Title: {title}...")
            print(f"  URL: {url}...")
            print(f"  Domain: {domain}")
            print(f"  Tone: {article.get('tone', 'N/A')}")
    else:
        print(f"[ERROR] GDELT API returned status {response.status_code}")
        sys.exit(1)

except Exception as e:
    print(f"[ERROR] Failed to connect to GDELT API: {e}")
    sys.exit(1)

# Test 2: Database Schema
print("\n\nTest 2: Verifying database schema...")
db = next(get_db())
try:
    result = db.execute(text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'niche_configs'
        AND column_name IN ('gdelt_enabled', 'gdelt_weight')
        ORDER BY column_name
    """))

    columns = {row[0]: row[1] for row in result.fetchall()}

    if 'gdelt_enabled' in columns and 'gdelt_weight' in columns:
        print("[OK] Database schema updated:")
        print(f"  - gdelt_enabled: {columns['gdelt_enabled']}")
        print(f"  - gdelt_weight: {columns['gdelt_weight']}")
    else:
        print("[ERROR] GDELT columns not found in database")
        sys.exit(1)

    # Check existing niches
    result = db.execute(text("""
        SELECT niche_name, gdelt_enabled, gdelt_weight
        FROM niche_configs
        WHERE is_active = 1
        LIMIT 3
    """))

    print("\nExisting niche configurations:")
    for row in result.fetchall():
        print(f"  - {row[0]}: enabled={row[1]}, weight={row[2]}")

finally:
    db.close()

# Test 3: SourceType Enum
print("\n\nTest 3: Verifying SourceType enum...")
try:
    from src.models.seed_topic import SourceType

    if hasattr(SourceType, 'GDELT'):
        print(f"[OK] GDELT source type exists: {SourceType.GDELT}")
    else:
        print("[ERROR] GDELT source type not found in SourceType enum")
        sys.exit(1)

except Exception as e:
    print(f"[ERROR] Failed to import SourceType: {e}")
    sys.exit(1)

# Test 4: HorizonScanner GDELT initialization
print("\n\nTest 4: Testing HorizonScanner GDELT initialization...")
db = next(get_db())
try:
    scanner = HorizonScanner(db)
    scanner._init_gdelt()

    if scanner.gdelt_enabled:
        print("[OK] GDELT initialized in HorizonScanner")
    else:
        print("[WARNING] GDELT not enabled in HorizonScanner (check settings)")

finally:
    db.close()

print("\n\n=== All Tests Passed! ===")
print("\nNext Steps:")
print("1. Start FastAPI server: uvicorn src.main:app --reload --port 8001")
print("2. Test Robot 1 with GDELT:")
print("   curl -X POST http://localhost:8001/api/robots/horizon-scanner/run \\")
print("     -H 'Content-Type: application/json' \\")
print("     -d '{\"niche_id\": 1, \"max_topics\": 20}'")
