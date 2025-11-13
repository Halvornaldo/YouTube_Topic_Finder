# CLAUDE.md - YouTube Topic Finder

## Project Overview

YouTube Topic Finder is an automated topic discovery tool using a 4-robot microservice architecture to identify high-opportunity YouTube content ideas. Now powered by Supabase cloud infrastructure with plans for a highly configurable React dashboard.

## Architecture

### 4-Robot Microservice System

1. **Robot 1 - Horizon Scanner** (`src/robots/horizon_scanner.py`) ✅ COMPLETE & TESTED
   - Discovers trending "seed topics" from external sources
   - Data Sources: Google Trends (pytrends - currently 404), Reddit (praw - working)
   - Credential Loading: Database → Environment fallback pattern (see Troubleshooting section)
   - Output: Seed topics stored in `seed_topics` table
   - Status: Successfully saving data to Supabase, full pipeline tested
   - Details: See `src/robots/horizon_scanner.py:60-90` for credential helper pattern

2. **Robot 2 - SERP Scraper** (`src/robots/serp_scraper.py`) ✅ COMPLETE & TESTED
   - Scrapes YouTube search results for candidate videos
   - Hybrid approach: Playwright scraping + YouTube API fallback
   - Avoids rate limiting and blocks
   - Output: Video candidates stored in `videos` table
   - Status: Full pipeline tested, successfully finding and storing videos
   - Details: See `docs/ROBOT2_IMPLEMENTATION_SUMMARY.md`

3. **Robot 3 - Metric Analyzer** (`src/robots/metric_analyzer.py`) ✅ COMPLETE & TESTED
   - Calculates opportunity scores for videos
   - APIs: YouTube Data API v3 (working), Google Ads API (configured, awaiting developer token approval)
   - Metrics: Search volume, competition, view velocity, engagement, recency (sentiment deferred)
   - Scoring: 6 configurable components with weighted average (0-100 scale)
   - Output: Metrics stored in `video_metrics` and `opportunity_scores` tables
   - Status: Full pipeline tested, analyzed 30 videos successfully with 0 failures
   - Details: See `docs/ROBOT3_IMPLEMENTATION_SUMMARY.md`

4. **Robot 4 - Format Classifier** (`src/robots/format_classifier.py`) 🔜
   - Predicts winning video formats
   - Process: Download audio (pytube) → Transcribe (OpenAI Whisper) → Analyze (NLP)
   - Formats: Tutorial, Listicle, News, Review, etc.
   - Output: Format predictions stored in `video_formats` table

## Configuration System ✅ COMPLETED

### Incremental Development Strategy
The system is designed to be **fully configurable from a React dashboard**. Configuration infrastructure is built **incrementally** alongside each robot:

- **Robot 1 (Horizon Scanner)**: Full configuration support ✅ COMPLETE
- **Robot 2 (SERP Scraper)**: Full configuration support ✅ COMPLETE
- **Robot 3 (Metric Analyzer)**: Full configuration support ✅ COMPLETE (24 settings)
- **Robot 4 (Format Classifier)**: Will receive same configuration treatment
- **Philosophy**: Build config APIs with each robot, not as separate phase
- **Pattern Documented**: See `docs/ROBOT_DEVELOPMENT_PATTERN.md` for standardized approach

### Storage Architecture

**Database-First Approach:**
- **Primary**: Supabase PostgreSQL (dynamic, user-created configs)
- **Templates**: YAML files in `config/templates/niches/` (read-only examples)
- **Sync**: One-way on startup (YAML templates → Database)
- **Philosophy**: Users configure everything from dashboard; database is source of truth

**Hot-reload System:**
- ✅ **Hot-reloadable**: Niche settings, scoring thresholds, robot behavior (ROBOT1_MAX_TOPICS, delays, etc.)
- ⚠️ **Requires restart**: DATABASE_URL, API keys (security-sensitive), REDIS_URL
- Controlled per-setting via `app_settings.requires_restart` column

### Configuration Capabilities

**What's Configurable:**
- ✅ Niche settings (keywords, subreddits, thresholds)
- ✅ Robot behavior (max topics, delays, enabled/disabled flags)
- ✅ API keys and credentials (encrypted)
- ✅ Processing limits (quotas, timeouts, concurrency)

**Apply Methods:**
- Hybrid approach: Critical settings hot-reload instantly, sensitive ones require restart
- ConfigManager service handles reload logic
- Dashboard shows which changes need restart

**Real-time Features:**
- Server-Sent Events (SSE) for job progress
- Live robot status updates
- New discovery streaming
- Job completion notifications

**Testing & Validation:**
- Test configs before saving
- Validate Reddit/YouTube API connections
- Dry-run mode for robots

## Database Schema (11 Tables in Supabase)

### Core Tables
1. **seed_topics** - Trending topics from Robot 1 ✅
2. **videos** - Candidate videos from Robot 2
3. **video_metrics** - Raw metrics from Robot 3
4. **opportunity_scores** - Calculated scores from Robot 3
5. **video_formats** - Format classifications from Robot 4

### Supporting Tables
6. **search_queries** - Track searches and their metadata
7. **content_gaps** - Identified market gaps

### Configuration & Monitoring Tables
8. **niche_configs** - User-created and template niches ✅
9. **app_settings** - All robot settings, API keys, processing limits (hot-reload flags)
10. **job_status** - Real-time job tracking, progress, current step
11. **config_history** - Version history of all configuration changes

## Tech Stack

- **Backend:** FastAPI (Python 3.11+) on port 8000
- **Database:** Supabase PostgreSQL (Cloud-hosted)
  - Project ID: etaacgjaghqoorbrfqzh
  - Dashboard: https://supabase.com/dashboard/project/etaacgjaghqoorbrfqzh
- **Cache/Queue:** Redis 7+ on port 6379 (local Docker container)
- **APIs:**
  - Google Trends (pytrends) - Currently returning 404 errors
  - Reddit (praw) - Working
  - YouTube Data API v3
  - Google Ads API
  - OpenAI Whisper API
- **Scraping:** Playwright (headless browser)
- **Audio:** pytube (download), OpenAI Whisper (transcription)
- **Frontend (Planned):** React with real-time configuration dashboard

## Project Structure

```
YouTube_Topic_Finder/
├── src/
│   ├── api/                      # FastAPI endpoints
│   │   ├── niches.py            # Niche CRUD, test, export/import
│   │   ├── settings.py          # Settings management (hot-reload)
│   │   ├── jobs.py              # Job monitoring and control
│   │   ├── validation.py        # Config testing and validation
│   │   ├── events.py            # SSE for real-time updates
│   │   ├── robots.py            # Robot triggers
│   │   ├── opportunities.py     # Results endpoints
│   │   └── health.py            # Health checks
│   ├── robots/                   # 4 robot implementations
│   │   └── horizon_scanner.py   # Robot 1 (working with ConfigManager)
│   ├── models/                   # SQLAlchemy models
│   │   ├── niche_config.py      # Niche configurations
│   │   ├── app_setting.py       # Application settings
│   │   ├── job_status.py        # Job tracking
│   │   ├── config_history.py    # Config version history
│   │   └── ...                  # Other data models
│   ├── services/                 # Business logic layer
│   │   ├── config_service.py    # ConfigManager with hot-reload
│   │   ├── niche_service.py     # Niche CRUD operations
│   │   ├── job_service.py       # Job management and tracking
│   │   └── validation_service.py # Config validation and testing
│   ├── schemas/                  # Pydantic validation schemas
│   ├── utils/                    # Helpers and utilities
│   └── config/                   # Configuration management
├── migrations/                   # Database migrations (Alembic)
├── config/
│   └── templates/                # YAML template configs (read-only)
│       └── niches/              # Niche templates
├── docs/                         # Documentation
│   └── CONFIGURATION.md         # Configuration system guide
├── tests/                        # Test suite
└── scripts/                      # Utility scripts
```

## Development Workflow

### Current Status
1. ✅ Project structure + documentation
2. ✅ Database schema (Supabase cloud) - 11 tables
3. ✅ FastAPI backend foundation
4. ✅ Robot 1 (Horizon Scanner) - COMPLETE & TESTED
5. ✅ Migrated from Docker PostgreSQL to Supabase
6. ✅ **Comprehensive Configuration System** - COMPLETE
   - ✅ Niche CRUD API (tested)
   - ✅ Settings Management API (tested)
   - ✅ Job Monitoring API (tested)
   - ✅ SSE Event Streaming (tested)
   - ✅ ConfigManager service with hot-reload
   - ✅ Template seeding from YAML
   - ✅ Validation and testing endpoints
7. ✅ **All APIs Tested** - Full CRUD operations verified
8. ✅ **Robot Development Pattern** - Documented for Robots 2-4
9. ✅ **Robot 2 (SERP Scraper)** - COMPLETE & TESTED
10. ✅ **Robot 3 (Metric Analyzer)** - COMPLETE & TESTED
   - ✅ Service layer with 30+ business logic methods
   - ✅ YouTube Data API integration
   - ✅ Google Ads API configured (awaiting developer token)
   - ✅ 6-component scoring algorithm with configurable weights
   - ✅ Hybrid video selection (IDs, search, topic, niche, all)
   - ✅ 24 configuration settings initialized
   - ✅ API endpoint with comprehensive documentation
11. ✅ **Full Pipeline Integration (Robot 1→2→3)** - TESTED & WORKING (2025-11-13)
   - ✅ End-to-end flow: Topics → Videos → Opportunity Scores
   - ✅ ConfigManager session fix: Dictionary metadata storage prevents DetachedInstanceError
   - ✅ Credential loading: Database → Environment fallback pattern
   - ✅ Results: 30 videos analyzed with 0 failures, opportunity scores 35-61
12. 🔜 Robot 4 (Format Classifier)
13. 🔜 React Dashboard with real-time configuration

### Running the System

```bash
# 1. Start Redis only (PostgreSQL is on Supabase cloud)
docker-compose up -d redis

# 2. Create tables in Supabase (first time only)
python create_supabase_tables.py

# 3. Start FastAPI server
uvicorn src.main:app --reload --port 8000

# 4. Trigger Robot 1 (Horizon Scanner)
curl -X POST http://localhost:8000/api/robots/horizon-scanner/run \
  -H "Content-Type: application/json" \
  -d '{"niche": "ai_tech", "max_topics": 20}'
```

## Configuration System

### YAML-based niche configurations
Located in `config/niches/`:
- `ai_tech.yaml` - AI/Tech niche
- `trending_viral.yaml` - Trending/Viral content
- `tech_news.yaml` - Tech News
- `gaming.yaml` - Gaming
- `finance_crypto.yaml` - Finance/Crypto

### React Dashboard (Planned)
The system will be highly configurable through a React dashboard that provides:
- Real-time configuration updates without server restarts
- Visual niche management and testing
- Live monitoring of robot activities
- Analytics and opportunity score visualization
- Export controls for different formats
- Webhook integrations
- Schedule management for automated runs

## Output Format

JSON prompts for AI video generator:

```json
{
  "topic": "AI Image Generation Tools 2025",
  "opportunity_score": 87.5,
  "search_volume": 45000,
  "competition": "medium",
  "predicted_format": "Tutorial",
  "format_confidence": 0.89,
  "content_gap": "No tutorials for beginners",
  "suggested_angle": "Beginner-friendly comparison",
  "keywords": ["AI image", "Midjourney", "DALL-E", "tutorial"],
  "prompt_for_generator": "Create a beginner-friendly tutorial..."
}
```

## Key Features

1. **Multi-source Discovery:** Combines Google Trends + Reddit for comprehensive coverage
2. **Smart Scraping:** Hybrid Playwright + API approach avoids detection
3. **Opportunity Scoring:** Multi-factor analysis (volume, competition, velocity, sentiment)
4. **Format Intelligence:** AI-powered format prediction from transcripts
5. **Content Gap Analysis:** Identifies underserved market opportunities
6. **Highly Configurable:** YAML configs + planned React dashboard for real-time adjustments
7. **Cloud-Native:** Supabase provides scalable PostgreSQL with real-time features

## Environment Variables

Required in `.env`:

```env
# Supabase Database (Cloud PostgreSQL)
DATABASE_URL=postgresql://postgres.etaacgjaghqoorbrfqzh:[PASSWORD]@aws-1-eu-north-1.pooler.supabase.com:6543/postgres

# Redis (Local)
REDIS_URL=redis://localhost:6379/0

# API Keys
YOUTUBE_API_KEY=your_youtube_api_key
GOOGLE_ADS_DEVELOPER_TOKEN=your_google_ads_token
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
OPENAI_API_KEY=your_openai_api_key

# Configuration
DEFAULT_NICHE=ai_tech
ROBOT1_MAX_TOPICS_PER_RUN=20
LOG_LEVEL=INFO
```

## Current Development Status

**Completed:**
- [x] Project structure
- [x] Database schema (Supabase) - 11 tables with migrations
- [x] FastAPI backend foundation
- [x] **Robot 1 (Horizon Scanner)** - Fully integrated and tested
  - [x] Credential loading pattern (database → environment fallback)
  - [x] Reddit integration working
  - [x] Saving topics to Supabase
- [x] **Robot 2 (SERP Scraper)** - Fully integrated and tested
  - [x] YouTube API integration
  - [x] Video discovery and storage
- [x] **Robot 3 (Metric Analyzer)** - Fully integrated and tested
  - [x] YouTube Data API metrics collection
  - [x] 6-component scoring algorithm
  - [x] 24 configuration settings
  - [x] Opportunity score calculation
- [x] Supabase migration
- [x] **Configuration System** - Complete with all APIs
  - [x] Niche Management API (CRUD, import/export, validation)
  - [x] Settings Management API (hot-reload support)
  - [x] Job Monitoring API (real-time tracking)
  - [x] SSE Event Streaming (live updates)
  - [x] Validation & Testing API
  - [x] ConfigManager session fix (dictionary metadata storage)
- [x] **Template System** - YAML templates seeded to database
- [x] **Comprehensive Testing** - All APIs tested and verified
- [x] **Development Pattern** - Documented for future robots
- [x] **Full Pipeline Integration (Robot 1→2→3)** - Tested & working
  - [x] End-to-end data flow verified
  - [x] 30 videos analyzed with 0 failures
  - [x] Opportunity scores 35-61 range
- [x] Documentation updates with troubleshooting guide

**Ready to Start:**
- [ ] Robot 4 (Format Classifier) - Pattern defined, ready to implement

**Pending:**
- [ ] React Dashboard with real-time configuration
- [ ] Google Ads API developer token approval (for search volume data)

## Next Steps

Now that full pipeline (Robot 1→2→3) is working:
1. **Robot 4 (Format Classifier)** - Follow established pattern
   - Use `_get_credential()` pattern for API keys (OpenAI Whisper)
   - Integrate with ConfigManager (avoid session issues - use dict metadata)
   - Use JobService for progress tracking
   - Add comprehensive configuration settings
   - Thoroughly test before integrating into pipeline
2. **Google Ads API Developer Token** - Submit application
   - Enables search volume data in Robot 3
   - Currently Robot 3 works without it (scores based on other 5 components)
3. **React Dashboard** - Build with Supabase real-time features
   - Real-time configuration management
   - Live robot monitoring
   - Opportunity score visualization
   - Niche management UI
4. **Production Deployment**
   - Environment hardening
   - API rate limiting
   - Automated testing suite
   - Monitoring and alerting

## Testing Summary

All systems tested and verified:
- ✅ Template seeding (5 YAML templates loaded) - 2025-11-11
- ✅ Niche CRUD operations (CREATE, READ, UPDATE, DELETE) - 2025-11-11
- ✅ Settings management (CREATE, READ, DELETE) - 2025-11-11
- ✅ Job monitoring endpoints - 2025-11-11
- ✅ SSE event streaming (connection established) - 2025-11-11
- ✅ Trailing slash handling fixed for all endpoints - 2025-11-11
- ✅ Robot 1 integration with configuration system - 2025-11-11
- ✅ **Full pipeline integration (Robot 1→2→3)** - 2025-11-13
  - Robot 1: 5 topics discovered from Reddit
  - Robot 2: 2 videos found and stored
  - Robot 3: 30 videos analyzed, 0 failures
  - API: Top 10 opportunities queryable with scores 50-61

## Troubleshooting

### Credential Loading Issues

**Problem**: API credentials not working (empty strings, "not configured" errors)

**Root Cause**: Credentials stored as empty strings in database override valid `.env` values

**Solution Pattern** (see `src/robots/horizon_scanner.py:60-90`):
```python
def _get_credential(self, db_key: str, env_value: Optional[str], name: str) -> Optional[str]:
    """
    Get credential with proper fallback logic.

    Priority:
    1. Database (if set and non-empty)
    2. Environment variable (from .env via settings)
    """
    # Try database first
    db_value = self.config_manager.get(db_key, None, 'api_keys')

    # Use database value if it exists and is non-empty
    if db_value and isinstance(db_value, str) and db_value.strip():
        logger.info(f"{name} loaded from database")
        return db_value.strip()

    # Fall back to environment
    if env_value and isinstance(env_value, str) and env_value.strip():
        logger.info(f"{name} loaded from environment (.env)")
        return env_value.strip()

    # Not found in either location
    return None
```

**Usage**:
```python
client_id = self._get_credential('reddit.client_id', settings.REDDIT_CLIENT_ID, 'Reddit Client ID')
client_secret = self._get_credential('reddit.client_secret', settings.REDDIT_CLIENT_SECRET, 'Reddit Client Secret')
```

**Debugging Credentials**:
```bash
# Check database credentials
python scripts/check_db_credentials.py

# Check environment settings
python scripts/test_settings.py

# Expected log output (when working):
# "Reddit Client ID loaded from environment (.env)"
# "Reddit Client Secret loaded from environment (.env)"
```

### ConfigManager Session Issues

**Problem**: `DetachedInstanceError: Instance <AppSetting> is not bound to a Session`

**Root Cause**: ConfigManager stored SQLAlchemy ORM objects in `_metadata` dict. When robots run as async background tasks, accessing ORM attributes (e.g., `metadata.category`) tries to lazy-load from a detached session.

**Solution** (see `src/services/config_manager.py:86-91`):
```python
# WRONG - stores ORM object
self._metadata[setting.key] = setting  # Will cause DetachedInstanceError

# CORRECT - stores plain dictionary
self._metadata[setting.key] = {
    'category': setting.category,
    'data_type': setting.data_type,
    'requires_restart': setting.requires_restart,
    'description': setting.description
}
```

**Access Pattern**:
```python
# WRONG - attribute access on ORM object
if metadata.category == 'api_keys':

# CORRECT - dict.get() on plain dictionary
if metadata.get('category') == 'api_keys':
```

**All Changes Required** (4 locations in config_manager.py):
1. Line 86-91: Store dict in `_load_settings()`
2. Line 116: Change to `metadata.get('category')`
3. Line 140: Change to `metadata.get('category')`
4. Line 378: Change to `metadata.get('requires_restart')`
5. Line 412: Change to `metadata.get('requires_restart', False)`

### Python Bytecode Cache Issues

**Problem**: Code changes not taking effect, old bugs reappearing

**Root Cause**: Python executing cached `.pyc` files instead of updated source code

**Solution**:
```bash
# 1. Kill all Python processes
taskkill //F //IM python.exe

# 2. Clear bytecode cache
rm -rf src/robots/__pycache__
rm -rf src/services/__pycache__
rm -rf src/__pycache__

# 3. Restart with -B flag (disables bytecode writing)
./venv/Scripts/python -B -m uvicorn src.main:app --reload --port 8001
```

**Prevention**: Always use `-B` flag during active development to disable bytecode caching.

## Important Changes from Original Design

1. **Database**: Migrated from local Docker PostgreSQL to Supabase cloud
   - Eliminates Windows Docker networking issues
   - Provides real-time subscriptions for React dashboard
   - Automatic backups and scaling

2. **Infrastructure**: Only Redis runs locally in Docker
   - Simpler setup
   - Cloud-first architecture

3. **Frontend Plans**: React dashboard will leverage Supabase features
   - Real-time data updates
   - Authentication ready
   - Direct database access via Supabase JS client

## Notes for Claude

### General Guidelines
- This is an **internal tool for personal use**
- Build **incrementally** - one robot at a time
- **Test thoroughly** before moving to next robot
- Keep code **well-documented** for pause/resume
- Follow **existing patterns** in codebase
- All robots should be **independently testable**
- Use **async/await** for I/O operations
- Implement proper **error handling** and **logging**
- **React Dashboard** should be highly configurable and real-time
- Leverage **Supabase features** for real-time updates and authentication

### Critical Patterns (Lessons Learned)

**1. Credential Loading (Database → Environment Fallback)**
- ALWAYS implement `_get_credential()` helper for API keys
- Database values take precedence IF non-empty
- Environment variables (.env) are fallback
- Log which source was used for debugging
- Handle empty strings explicitly (`.strip()`)
- See: `src/robots/horizon_scanner.py:60-90`

**2. ConfigManager in Async Contexts (Session Management)**
- NEVER store SQLAlchemy ORM objects in instance variables
- ALWAYS extract primitive values or dictionaries immediately
- Background tasks run in different async contexts
- ORM lazy-loading fails on detached instances
- Use `dict.get()` instead of attribute access for safety
- See: `src/services/config_manager.py:86-91`

**3. Python Bytecode Caching**
- ALWAYS use `-B` flag during active development
- Clear `__pycache__` directories when debugging stale code
- Kill all Python processes before restarting
- Bytecode cache can persist bugs even after code fixes

**4. FastAPI Background Tasks**
- Jobs run in separate async contexts from request handlers
- Database sessions must be managed carefully
- Log extensively for debugging async execution
- ConfigManager singleton must be thread/async-safe

**5. Testing Full Pipeline**
- Test each robot independently first
- Then test sequential pairs (1→2, 2→3)
- Finally test complete pipeline (1→2→3)
- Verify data persisted at each stage
- Check API endpoints return expected results