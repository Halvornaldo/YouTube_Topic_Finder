# CLAUDE.md - YouTube Topic Finder

## Project Overview

YouTube Topic Finder is an automated topic discovery tool using a 4-robot microservice architecture to identify high-opportunity YouTube content ideas.

## Architecture

### 4-Robot Microservice System

1. **Robot 1 - Horizon Scanner** (`src/robots/horizon_scanner.py`)
   - Discovers trending "seed topics" from external sources
   - Data Sources: Google Trends (pytrends), Reddit (praw)
   - Output: Seed topics stored in `seed_topics` table

2. **Robot 2 - SERP Scraper** (`src/robots/serp_scraper.py`)
   - Scrapes YouTube search results for candidate videos
   - Hybrid approach: Playwright scraping + YouTube API fallback
   - Avoids rate limiting and blocks
   - Output: Video candidates stored in `videos` table

3. **Robot 3 - Metric Analyzer** (`src/robots/metric_analyzer.py`)
   - Calculates opportunity scores for videos
   - APIs: YouTube Data API v3, Google Ads API
   - Metrics: Search volume, competition, view velocity, sentiment
   - Output: Metrics stored in `video_metrics` and `opportunity_scores` tables

4. **Robot 4 - Format Classifier** (`src/robots/format_classifier.py`)
   - Predicts winning video formats
   - Process: Download audio (pytube) → Transcribe (OpenAI Whisper) → Analyze (NLP)
   - Formats: Tutorial, Listicle, News, Review, etc.
   - Output: Format predictions stored in `video_formats` table

## Database Schema (9 Tables)

### Core Tables
1. **seed_topics** - Trending topics from Robot 1
2. **videos** - Candidate videos from Robot 2
3. **video_metrics** - Raw metrics from Robot 3
4. **opportunity_scores** - Calculated scores from Robot 3
5. **video_formats** - Format classifications from Robot 4

### Supporting Tables
6. **search_queries** - Track searches and their metadata
7. **content_gaps** - Identified market gaps
8. **niche_configs** - YAML-based niche configurations
9. **processing_jobs** - Job queue tracking

## Tech Stack

- **Backend:** FastAPI (Python 3.11+) on port 8000
- **Database:** PostgreSQL 15+ on port 5432 (DB: youtube_topic_finder)
- **Queue:** Redis 7+ on port 6379
- **APIs:**
  - Google Trends (pytrends)
  - Reddit (praw)
  - YouTube Data API v3
  - Google Ads API
  - OpenAI Whisper API
- **Scraping:** Playwright (headless browser)
- **Audio:** pytube (download), OpenAI Whisper (transcription)

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
├── docker/              # Docker configurations
└── scripts/             # Utility scripts
```

## Development Workflow

### Incremental Build Process
1. ✅ Project structure + documentation
2. ✅ Database schema + migrations
3. ✅ FastAPI backend foundation
4. ✅ Robot 1 (Horizon Scanner)
5. ⏸️ Test Robot 1 before continuing
6. 🔜 Robot 2 (SERP Scraper)
7. 🔜 Robot 3 (Metric Analyzer)
8. 🔜 Robot 4 (Format Classifier)
9. 🔜 Integration + full pipeline testing

### Pause/Resume Guidelines

When resuming development:
1. Check the `Development Workflow` section above for current status
2. Review recent commits with `git log`
3. Check TODO comments in code (`grep -r "TODO" src/`)
4. Review `docs/development.md` for current sprint goals
5. Run tests: `pytest tests/` to ensure nothing broke

### Running the System

```bash
# 1. Start infrastructure
docker-compose up -d postgres redis

# 2. Run migrations
alembic upgrade head

# 3. Start FastAPI server
uvicorn src.main:app --reload --port 8000

# 4. Trigger Robot 1 (Horizon Scanner)
curl -X POST http://localhost:8000/api/robots/horizon-scanner/run
```

## Configuration System

YAML-based niche configurations in `config/niches/`:
- `ai_tech.yaml` - AI/Tech niche
- `trending_viral.yaml` - Trending/Viral content
- `tech_news.yaml` - Tech News
- `gaming.yaml` - Gaming
- `finance_crypto.yaml` - Finance/Crypto

Each config defines:
- Keywords and search terms
- Platform priorities (Google Trends weight, Reddit weight)
- Thresholds for opportunity scoring
- Format preferences

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
6. **Customizable Niches:** YAML configs for different content categories

## Environment Variables

Required in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/youtube_topic_finder

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
YOUTUBE_API_KEY=your_youtube_api_key
GOOGLE_ADS_DEVELOPER_TOKEN=your_google_ads_token
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
OPENAI_API_KEY=your_openai_api_key

# Configuration
DEFAULT_NICHE=ai_tech
LOG_LEVEL=INFO
```

## Current Development Status

**Completed:**
- [ ] Project structure
- [ ] Database schema
- [ ] FastAPI backend foundation
- [ ] Robot 1 (Horizon Scanner)

**In Progress:**
- [x] Documentation

**Pending:**
- [ ] Robot 2 (SERP Scraper)
- [ ] Robot 3 (Metric Analyzer)
- [ ] Robot 4 (Format Classifier)
- [ ] Full pipeline integration

## Next Steps

After Robot 1 is tested and working:
1. Implement Robot 2 with Playwright scraping
2. Add YouTube API fallback mechanism
3. Implement rate limiting and retry logic
4. Continue to Robot 3 and 4

## Notes for Claude

- This is an **internal tool for personal use**
- Build **incrementally** - one robot at a time
- **Test thoroughly** before moving to next robot
- Keep code **well-documented** for pause/resume
- Follow **existing patterns** in codebase
- All robots should be **independently testable**
- Use **async/await** for I/O operations
- Implement proper **error handling** and **logging**
