# Robot 2 Design Document: SERP Scraper

## Phase 1: Planning & Design

### Robot Responsibilities
**Robot 2 (SERP Scraper)** takes seed topics from Robot 1 and finds candidate YouTube videos by:
1. Taking seed topics from `seed_topics` table (where `processed = 0`)
2. Performing YouTube searches using hybrid approach:
   - **Primary:** Playwright browser automation (avoids rate limits, gets fresh results)
   - **Fallback:** YouTube Data API v3 (when Playwright fails or is disabled)
3. Extracting video metadata (title, video_id, channel, view count, etc.)
4. Saving videos to `videos` table with search context
5. Marking seed topics as `processed = 1`

### Data Flow
```
seed_topics (processed=0)
    ↓
Robot 2 (SERP Scraper)
    ↓
search_queries (query tracking)
    ↓
videos (candidate videos)
```

### Database Tables
✅ **Already exist:**
- `videos` - Candidate videos (src/models/video.py)
- `search_queries` - Search tracking (src/models/search_query.py)
- `seed_topics` - Input topics (src/models/seed_topic.py)

**No new tables needed.** Models are already complete with all required columns.

### Configuration Parameters

**Robot 2 Settings (to be added to `app_settings`):**
- `ROBOT2_ENABLED` (boolean, default: true) - Enable/disable robot
- `ROBOT2_MAX_VIDEOS_PER_QUERY` (integer, default: 20) - Max videos to scrape per search
- `ROBOT2_USE_PLAYWRIGHT` (boolean, default: true) - Toggle browser automation
- `ROBOT2_HEADLESS` (boolean, default: true) - Browser headless mode
- `ROBOT2_YOUTUBE_API_FALLBACK` (boolean, default: true) - Enable API fallback
- `ROBOT2_DELAY_BETWEEN_SEARCHES` (integer, default: 3) - Delay in seconds
- `ROBOT2_MAX_TOPICS_PER_RUN` (integer, default: 10) - Topics to process per run
- `ROBOT2_SCREENSHOT_ON_ERROR` (boolean, default: false) - Save screenshots on errors
- `ROBOT2_USER_AGENT` (string) - Custom user agent for browser

**API Keys (already in system):**
- `youtube.api_key` - YouTube Data API v3 key

### API Endpoints

**POST /api/robots/serp-scraper/run**
- Trigger Robot 2 for a specific niche
- Request: `{"niche_name": "ai_tech", "max_topics": 10}`
- Response: Job ID and initial status

**GET /api/robots/serp-scraper/status**
- Get current robot status and stats
- Response: Running status, last run results, error states

**GET /api/robots/serp-scraper/results**
- Get videos found by Robot 2
- Query params: `niche`, `limit`, `offset`
- Response: List of videos with metadata

### Testing Strategy

**Unit Tests:**
- Video extraction from YouTube HTML
- YouTube API response parsing
- Fallback logic (Playwright → API)
- Rate limiting delays

**Integration Tests:**
- Full search flow (seed topic → search → save videos)
- ConfigManager integration
- JobService progress tracking
- Database persistence

**API Tests:**
- POST /api/robots/serp-scraper/run (with ai_tech niche)
- Monitor job progress via /api/jobs/{job_id}
- Verify videos saved to database
- Test error handling (invalid niche, API failures)

**Manual Tests:**
- Run with Playwright enabled (check browser automation)
- Run with Playwright disabled (test API fallback)
- Test rate limiting (verify delays)
- Verify SSE events broadcast correctly

## Phase 2: Implementation Plan

### Step 1: Database Models ✅
- Models already exist and are complete
- No migration needed

### Step 2: Robot Service
Create `src/robots/serp_scraper.py`:
- `SerpScraper` class
- `__init__` with ConfigManager integration
- `run(niche_name, max_topics)` - Main entry point
- `_scrape_with_playwright(query)` - Browser automation
- `_scrape_with_api(query)` - API fallback
- `_extract_video_data(html)` - Parse video info
- `_save_video(video_data, search_query_id)` - Database save

### Step 3: Business Logic Layer
Create `src/services/serp_scraper_service.py`:
- `SerpScraperService` class
- CRUD operations for videos
- Search query tracking
- Video deduplication logic
- Statistics and reporting

### Step 4: API Endpoints
Update `src/api/robots.py`:
- Add SerpScraperRequest/Response models
- Implement POST /serp-scraper/run
- Implement GET /serp-scraper/status
- Implement GET /serp-scraper/results

## Dependencies

**New packages needed:**
- `playwright` - Browser automation
- `google-api-python-client` - YouTube Data API v3 (may already be installed)

**Install:**
```bash
pip install playwright google-api-python-client
playwright install chromium
```

## Success Criteria

Robot 2 is complete when:
- ✅ Can scrape YouTube search results via Playwright
- ✅ Falls back to API when Playwright fails
- ✅ Saves videos with complete metadata
- ✅ Marks seed topics as processed
- ✅ Tracks all searches in search_queries table
- ✅ Integrates with ConfigManager
- ✅ Reports progress via JobService
- ✅ Broadcasts SSE events
- ✅ API endpoints return 200 OK
- ✅ All tests pass

---

**Created:** 2025-11-11
**Status:** Planning Complete - Ready for Implementation
