# GDELT Integration for Robot 1 (Horizon Scanner)

## Overview

GDELT (Global Database of Events, Language and Tone) has been integrated into Robot 1 as a free, unlimited alternative to Google Trends for discovering trending topics. This eliminates the dependency on the broken `pytrends` library.

**Implementation Date:** 2025-11-13
**Status:** ✅ Complete and Tested

## Why GDELT?

- **Free & Unlimited:** No API key required, no rate limits, completely free
- **Global Coverage:** Monitors news from every country in 65 languages
- **Real-time:** Updates every 15 minutes with new global news coverage
- **Rich Metadata:** Provides tone analysis, themes, locations, and more
- **No Authentication:** Public API, no signup required

## What Was Implemented

### 1. Database Schema Changes

**File:** `src/models/niche_config.py`

Added two new columns to the `niche_configs` table:
- `gdelt_enabled` (Integer, default: 1) - Boolean flag to enable/disable GDELT
- `gdelt_weight` (Float, default: 0.5) - Weight for GDELT topics in scoring

**Migration:** `migrations/versions/20251113_1044_add_gdelt_columns_to_niche_configs.py`

Applied to Supabase database with script: `scripts/apply_gdelt_migration.py`

### 2. Model Changes

**File:** `src/models/seed_topic.py`

Added `GDELT = "gdelt"` to the `SourceType` enum:
```python
class SourceType(str, enum.Enum):
    """Source where the topic was discovered."""
    GOOGLE_TRENDS = "google_trends"
    REDDIT = "reddit"
    GDELT = "gdelt"  # NEW: GDELT news trending topics
    MANUAL = "manual"
```

### 3. Robot 1 Integration

**File:** `src/robots/horizon_scanner.py`

#### Added Methods:
1. **`_init_gdelt()`** (lines 138-150)
   - Initializes GDELT (no authentication required)
   - Checks if GDELT is enabled via ConfigManager
   - Sets `self.gdelt_enabled` flag

2. **`_scan_gdelt(config)`** (lines 495-608)
   - Queries GDELT 2.0 Doc API for trending news articles
   - Uses niche keywords to find relevant topics
   - Filters articles by tone (configurable, default: -5.0)
   - Returns top 20 articles per keyword
   - Calculates trend scores based on tone and recency
   - Broadcasts discovered topics via SSE events

#### Configuration Settings (ConfigManager):
- `robot1.gdelt.enabled` (bool, default: True) - Enable/disable GDELT
- `robot1.gdelt.timespan` (str, default: "3d") - Time range for articles (e.g., "3d", "1w")
- `robot1.gdelt.max_records` (int, default: 75) - Max articles to fetch per keyword
- `robot1.gdelt.min_tone` (float, default: -5.0) - Minimum tone threshold (-10 to +10)

#### Integration Points:
- **Line 221:** `self._init_gdelt()` - Initialize GDELT client
- **Lines 260-273:** GDELT scanning block in `run()` method
- **Line 189:** Added `gdelt_enabled` to job config snapshot
- **Line 289:** Added `gdelt` count to result summary

### 4. API Changes

GDELT topics are now included in Robot 1 results:
```json
{
  "status": "completed",
  "topics_found": 45,
  "topics_saved": 45,
  "google_trends": 10,
  "reddit": 20,
  "gdelt": 15
}
```

## GDELT API Details

### Endpoint
```
https://api.gdeltproject.org/api/v2/doc/doc
```

### Parameters
- `query`: Search term (e.g., "artificial intelligence")
- `mode`: "artlist" (list of articles)
- `maxrecords`: Maximum articles to return (default: 75)
- `format`: "json"
- `timespan`: Time range (e.g., "3d" for 3 days)
- `sort`: "hybridrel" (sort by relevance)

### Response Structure
```json
{
  "articles": [
    {
      "title": "Article title",
      "url": "https://example.com/article",
      "domain": "example.com",
      "tone": -2.5,  // -10 (very negative) to +10 (very positive)
      "seendate": "20251113120000"  // YYYYMMDDHHMMSS
    }
  ]
}
```

## Testing

### Test Script: `scripts/test_gdelt_integration.py`

Verifies:
1. ✅ GDELT API connectivity
2. ✅ Database schema (gdelt_enabled, gdelt_weight columns)
3. ✅ SourceType.GDELT enum value
4. ✅ HorizonScanner GDELT initialization

Run tests:
```bash
./venv/Scripts/python scripts/test_gdelt_integration.py
```

**Result:** All tests passed ✅

## Usage

### 1. Via API

```bash
curl -X POST http://localhost:8001/api/robots/horizon-scanner/run \
  -H "Content-Type: application/json" \
  -d '{"niche_id": 1, "max_topics": 20}'
```

### 2. Configure GDELT Settings

```python
from src.config.database import get_db
from src.services.config_manager import ConfigManager

db = next(get_db())
config = ConfigManager(db)

# Disable GDELT
config.set("robot1.gdelt.enabled", False, changed_by="user")

# Adjust timespan (last 7 days instead of 3)
config.set("robot1.gdelt.timespan", "7d", changed_by="user")

# Adjust min tone (only positive/neutral news)
config.set("robot1.gdelt.min_tone", 0.0, changed_by="user")
```

### 3. Niche-Level Configuration

Update `niche_configs` table directly or via API:
```python
niche.gdelt_enabled = 1  # Enable
niche.gdelt_weight = 0.7  # Higher weight = more GDELT topics
```

## Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `robot1.gdelt.enabled` | bool | True | Enable/disable GDELT scanning |
| `robot1.gdelt.timespan` | str | "3d" | Time range: "1d", "3d", "1w", "1m" |
| `robot1.gdelt.max_records` | int | 75 | Max articles per keyword |
| `robot1.gdelt.min_tone` | float | -5.0 | Filter by tone (-10 to +10) |
| `niche_configs.gdelt_enabled` | int | 1 | Per-niche enable flag |
| `niche_configs.gdelt_weight` | float | 0.5 | Per-niche topic weight |

## Benefits Over Google Trends

1. **No Rate Limits:** GDELT has no rate limits, unlike Google Trends which often returns 429 errors
2. **No Authentication:** No API keys or authentication required
3. **More Granular:** Article-level data instead of aggregate trends
4. **Richer Metadata:** Tone, domain, precise timestamps
5. **Global Coverage:** Monitors news from 195 countries in 65 languages
6. **Free Forever:** Funded by Google Jigsaw, completely free

## Future Enhancements

1. **GDELT Themes:** Use GDELT GKG themes API for broader topic discovery
2. **GDELT Events:** Incorporate event database for real-time breaking news
3. **Sentiment Filtering:** Advanced filtering by sentiment categories
4. **Geographic Filtering:** Filter by country/region for localized trends
5. **Language Support:** Multi-language topic discovery

## Related Files

- `src/robots/horizon_scanner.py` - Robot 1 implementation
- `src/models/seed_topic.py` - SeedTopic and SourceType models
- `src/models/niche_config.py` - NicheConfig model with GDELT fields
- `migrations/versions/20251113_1044_add_gdelt_columns_to_niche_configs.py` - Database migration
- `scripts/apply_gdelt_migration.py` - Migration script for Supabase
- `scripts/test_gdelt_integration.py` - Integration tests

## References

- [GDELT Project](https://www.gdeltproject.org/)
- [GDELT 2.0 Doc API Documentation](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)
- [GDELT Data Format](https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/)

## Status

**Implementation:** ✅ Complete
**Testing:** ✅ All tests passed
**Migration:** ✅ Applied to Supabase
**Ready for Production:** ✅ Yes
