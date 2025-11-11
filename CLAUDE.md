# CLAUDE.md - YouTube Topic Finder

## Project Overview

YouTube Topic Finder is an automated topic discovery tool using a 4-robot microservice architecture to identify high-opportunity YouTube content ideas. Now powered by Supabase cloud infrastructure with plans for a highly configurable React dashboard.

## Architecture

### 4-Robot Microservice System

1. **Robot 1 - Horizon Scanner** (`src/robots/horizon_scanner.py`) ✅ WORKING
   - Discovers trending "seed topics" from external sources
   - Data Sources: Google Trends (pytrends - currently 404), Reddit (praw - working)
   - Output: Seed topics stored in `seed_topics` table
   - Status: Successfully connected to Supabase and saving data

2. **Robot 2 - SERP Scraper** (`src/robots/serp_scraper.py`) 🔜
   - Scrapes YouTube search results for candidate videos
   - Hybrid approach: Playwright scraping + YouTube API fallback
   - Avoids rate limiting and blocks
   - Output: Video candidates stored in `videos` table

3. **Robot 3 - Metric Analyzer** (`src/robots/metric_analyzer.py`) 🔜
   - Calculates opportunity scores for videos
   - APIs: YouTube Data API v3, Google Ads API
   - Metrics: Search volume, competition, view velocity, sentiment
   - Output: Metrics stored in `video_metrics` and `opportunity_scores` tables

4. **Robot 4 - Format Classifier** (`src/robots/format_classifier.py`) 🔜
   - Predicts winning video formats
   - Process: Download audio (pytube) → Transcribe (OpenAI Whisper) → Analyze (NLP)
   - Formats: Tutorial, Listicle, News, Review, etc.
   - Output: Format predictions stored in `video_formats` table

## Database Schema (9 Tables in Supabase)

### Core Tables
1. **seed_topics** - Trending topics from Robot 1 ✅
2. **videos** - Candidate videos from Robot 2
3. **video_metrics** - Raw metrics from Robot 3
4. **opportunity_scores** - Calculated scores from Robot 3
5. **video_formats** - Format classifications from Robot 4

### Supporting Tables
6. **search_queries** - Track searches and their metadata
7. **content_gaps** - Identified market gaps
8. **niche_configs** - YAML-based niche configurations ✅
9. **processing_jobs** - Job queue tracking ✅

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
│   ├── api/              # FastAPI endpoints
│   ├── robots/           # 4 robot implementations
│   ├── models/           # SQLAlchemy models
│   ├── services/         # Business logic
│   ├── utils/            # Helpers and utilities
│   └── config/           # Configuration management
├── migrations/           # Database migrations (Alembic)
├── config/              # YAML configuration files
│   └── niches/          # Niche-specific configs
├── docs/                # Additional documentation
├── tests/               # Test suite
└── scripts/             # Utility scripts
```

## Development Workflow

### Current Status
1. ✅ Project structure + documentation
2. ✅ Database schema (Supabase cloud)
3. ✅ FastAPI backend foundation
4. ✅ Robot 1 (Horizon Scanner) - WORKING WITH SUPABASE
5. ✅ Migrated from Docker PostgreSQL to Supabase
6. 🔜 Robot 2 (SERP Scraper)
7. 🔜 Robot 3 (Metric Analyzer)
8. 🔜 Robot 4 (Format Classifier)
9. 🔜 React Dashboard with real-time configuration
10. 🔜 Integration + full pipeline testing

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
- [x] Database schema (Supabase)
- [x] FastAPI backend foundation
- [x] Robot 1 (Horizon Scanner)
- [x] Supabase migration
- [x] Documentation update

**In Progress:**
- [ ] Robot 2 (SERP Scraper)

**Pending:**
- [ ] Robot 3 (Metric Analyzer)
- [ ] Robot 4 (Format Classifier)
- [ ] React Dashboard
- [ ] Full pipeline integration

## Next Steps

Now that Robot 1 is working with Supabase:
1. Implement Robot 2 with Playwright scraping
2. Add YouTube API fallback mechanism
3. Implement rate limiting and retry logic
4. Continue to Robot 3 and 4
5. Build React dashboard with Supabase real-time features

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