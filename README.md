# YouTube Topic Finder

An automated YouTube topic discovery tool that identifies high-opportunity content ideas using a 4-robot microservice architecture and cloud infrastructure.

## Overview

YouTube Topic Finder analyzes trending topics across multiple platforms, scrapes video performance data, calculates opportunity scores, and predicts winning video formats - all to generate AI-ready content prompts. Built with modern cloud infrastructure (Supabase) and designed for a highly configurable React dashboard.

## Features

- **🔍 Multi-Source Discovery**: Scans Google Trends and Reddit for emerging topics
- **📊 Smart Scraping**: Hybrid Playwright + API approach for reliable data collection
- **💯 Opportunity Scoring**: Multi-factor analysis (search volume, competition, velocity, sentiment)
- **🎯 Format Prediction**: AI-powered video format classification from transcripts
- **🎨 Content Gap Analysis**: Identifies underserved market opportunities
- **⚙️ Fully Configurable**: Complete REST API for managing all settings, niches, and robot behavior from React dashboard
- **📡 Real-time Monitoring**: Live job progress, robot status, and data updates via Server-Sent Events
- **🧪 Test & Validate**: Test configurations before saving, validate API connections
- **☁️ Cloud-Native**: Powered by Supabase for scalable PostgreSQL hosting and real-time features

## Architecture

### 4-Robot System

1. **Horizon Scanner**: Discovers trending seed topics (Google Trends + Reddit) ✅
2. **SERP Scraper**: Scrapes YouTube search results (Playwright + API fallback) 🔜
3. **Metric Analyzer**: Calculates opportunity scores (YouTube Data API + Google Ads API) 🔜
4. **Format Classifier**: Predicts video formats (Whisper transcription + NLP analysis) 🔜

### Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: Supabase PostgreSQL (Cloud-hosted)
- **Cache/Queue**: Redis 7+
- **APIs**: YouTube Data API v3, Google Ads API, OpenAI Whisper
- **Scraping**: Playwright
- **Audio**: pytube
- **Frontend** (Planned): React with real-time configuration dashboard

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for Redis only)
- Supabase account (free tier works)
- API keys (YouTube, Reddit, OpenAI)

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd YouTube_Topic_Finder

# 2. Create virtual environment
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up Supabase
# Create a project at https://supabase.com
# Get your connection string from Settings > Database

# 5. Set up environment variables
cp .env.example .env
# Edit .env with your Supabase URL and API keys

# 6. Start Redis (only local service needed)
docker-compose up -d redis

# 7. Create database tables
python create_supabase_tables.py

# 8. Start the server
uvicorn src.main:app --reload --port 8000
```

### Environment Configuration

Required `.env` variables:

```env
# Supabase Database (Cloud PostgreSQL)
DATABASE_URL=postgresql://postgres.YOUR_PROJECT:[PASSWORD]@aws-1-eu-north-1.pooler.supabase.com:6543/postgres

# Redis (Local)
REDIS_URL=redis://localhost:6379/0

# API Keys
YOUTUBE_API_KEY=your_youtube_api_key_here
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Google Ads for search volume
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
GOOGLE_ADS_CLIENT_ID=your_client_id
GOOGLE_ADS_CLIENT_SECRET=your_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token

# Configuration
DEFAULT_NICHE=ai_tech
ROBOT1_MAX_TOPICS_PER_RUN=20
```

## Configuration System

The YouTube Topic Finder is designed to be **fully configurable** from a React dashboard through a comprehensive REST API. All settings, niches, and robot behavior can be managed without code changes.

### Configuration Approach

**Incremental Development:**
- Configuration infrastructure is built alongside each robot
- Robot 1 (Horizon Scanner) has full configuration support now
- Robots 2-4 will get the same treatment as they're developed

**Storage Strategy:**
- **Primary**: Supabase database (dynamic, user-created configurations)
- **Templates**: YAML files in `config/templates/niches/` (read-only examples)
- **Sync**: One-way on startup (YAML → Database for templates)

**Hot-reload Capabilities:**
- ✅ **Hot-reloadable**: Niche settings, scoring thresholds, robot behavior parameters
- ⚠️ **Requires restart**: Database URL, API keys, Redis URL
- Each setting flagged individually for reload behavior

### Configuration API Endpoints

**Niche Management:**
```bash
GET    /api/niches/                  # List all niches
POST   /api/niches/                  # Create new niche
GET    /api/niches/{id}              # Get niche details
PUT    /api/niches/{id}              # Update niche
DELETE /api/niches/{id}              # Delete niche
POST   /api/niches/{id}/test         # Test niche config
POST   /api/niches/import            # Import from JSON/YAML
GET    /api/niches/export/all        # Export all niches
```

**Settings Management:**
```bash
GET    /api/settings                 # Get all settings
PUT    /api/settings                 # Bulk update settings
PATCH  /api/settings/{key}           # Update single setting
POST   /api/settings/reload          # Hot-reload changed settings
```

**Job Monitoring:**
```bash
GET    /api/jobs                     # List recent jobs
GET    /api/jobs/{id}                # Get job details
DELETE /api/jobs/{id}                # Cancel running job
```

**Validation & Testing:**
```bash
POST   /api/validate/niche           # Validate niche config
POST   /api/validate/reddit          # Test Reddit API connection
POST   /api/validate/api-key         # Test API keys
```

**Real-time Events (Server-Sent Events):**
```bash
GET    /api/events/jobs/{id}         # Stream job progress
GET    /api/events/discoveries       # Stream new seed topics
GET    /api/events/robots            # Stream robot status
```

### React Dashboard Features

The React dashboard (in development) will provide:

- **✅ Full CRUD**: Create, read, update, delete niches and settings
- **✅ Real-time Monitoring**: Live job progress, robot status, data updates
- **✅ Test Before Save**: Validate configurations before applying
- **✅ Import/Export**: Backup and share configs in JSON/YAML
- **Visual Analytics**: Charts and graphs of opportunity scores (coming soon)
- **Pipeline Control**: Schedule and orchestrate robot runs (coming soon)
- **Webhook Integration**: Connect to external services (coming soon)

### YAML Templates vs Database

**YAML Templates** (`config/templates/niches/`):
- Shipped with the application as examples
- Read-only from the dashboard
- Can be cloned to create custom niches
- Loaded into database on first run

**Database Configurations**:
- User-created niches stored in Supabase
- Fully editable from dashboard
- Version tracked with history
- Can be exported to YAML for sharing

See `docs/CONFIGURATION.md` for detailed configuration guide.

## Usage

### Run Individual Robots

```bash
# Robot 1: Horizon Scanner (WORKING)
curl -X POST http://localhost:8000/api/robots/horizon-scanner/run \
  -H "Content-Type: application/json" \
  -d '{"niche": "ai_tech", "max_topics": 20}'

# Robot 2: SERP Scraper (Coming Soon)
curl -X POST http://localhost:8000/api/robots/serp-scraper/run \
  -H "Content-Type: application/json" \
  -d '{"topic_id": 1}'

# Robot 3: Metric Analyzer (Coming Soon)
curl -X POST http://localhost:8000/api/robots/metric-analyzer/run \
  -H "Content-Type: application/json" \
  -d '{"video_ids": [1, 2, 3]}'

# Robot 4: Format Classifier (Coming Soon)
curl -X POST http://localhost:8000/api/robots/format-classifier/run \
  -H "Content-Type: application/json" \
  -d '{"video_id": 1}'
```

### Get Results

```bash
# Get discovered topics
curl http://localhost:8000/api/seed-topics

# Get top opportunities (when available)
curl http://localhost:8000/api/opportunities?limit=10
```

## Output Format

JSON prompts ready for AI video generators:

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
  "prompt_for_generator": "Create a beginner-friendly tutorial comparing AI image generation tools..."
}
```

## Database Schema

11-table schema in Supabase cloud:

**Core Data Tables:**
- `seed_topics` - Trending topics discovered by Robot 1 ✅
- `videos` - Candidate videos from Robot 2
- `video_metrics` - Raw performance metrics from Robot 3
- `opportunity_scores` - Calculated opportunity scores
- `video_formats` - Format predictions from Robot 4
- `search_queries` - Search tracking
- `content_gaps` - Identified gaps

**Configuration & Monitoring:**
- `niche_configs` - User-created and template niches ✅
- `app_settings` - All robot settings, API keys, processing limits
- `job_status` - Real-time job tracking and progress
- `config_history` - Version history of all configuration changes

## Development

### Project Structure

```
YouTube_Topic_Finder/
├── src/
│   ├── api/                      # FastAPI routes
│   │   ├── niches.py            # Niche CRUD, test, export/import
│   │   ├── settings.py          # Settings management
│   │   ├── jobs.py              # Job monitoring
│   │   ├── validation.py        # Config testing
│   │   ├── events.py            # SSE for real-time updates
│   │   ├── robots.py            # Robot triggers
│   │   └── opportunities.py     # Results endpoints
│   ├── robots/                   # 4 robot implementations
│   │   └── horizon_scanner.py   # Robot 1 (working)
│   ├── models/                   # SQLAlchemy models
│   │   ├── niche_config.py      # Niche configurations
│   │   ├── app_setting.py       # Application settings
│   │   ├── job_status.py        # Job tracking
│   │   └── ...                  # Other data models
│   ├── services/                 # Business logic
│   │   ├── config_service.py    # ConfigManager (hot-reload)
│   │   ├── niche_service.py     # Niche CRUD operations
│   │   ├── job_service.py       # Job management
│   │   └── validation_service.py # Config validation
│   ├── schemas/                  # Pydantic schemas
│   ├── utils/                    # Utilities
│   └── config/                   # Config management
├── migrations/                   # Database migrations (Alembic)
├── config/
│   └── templates/                # YAML template configs
│       └── niches/              # Niche templates
├── tests/                        # Tests
└── docs/                         # Documentation
    └── CONFIGURATION.md         # Config system guide
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific robot tests
pytest tests/robots/test_horizon_scanner.py

# Run with coverage
pytest --cov=src tests/
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Supabase Dashboard

View and manage your data:

- **Database**: https://supabase.com/dashboard/project/YOUR_PROJECT_ID/editor
- **Table Editor**: Browse and edit data visually
- **SQL Editor**: Run custom queries
- **Real-time**: Monitor live changes

## Troubleshooting

### Common Issues

**Supabase connection errors:**
- Check your DATABASE_URL in .env
- Ensure you're using the Transaction Pooler connection string
- Verify your internet connection

**Redis connection errors:**
```bash
# Check Redis status
docker-compose ps redis

# Test connection
redis-cli ping
```

**Google Trends 404 error:**
- Known issue with pytrends library
- Does not affect functionality (Reddit still works)
- Will be fixed in future updates

**API rate limiting:**
- YouTube API: 10,000 units/day (check quota in Google Console)
- Reddit API: 60 requests/minute (adjust delay in config)

## Roadmap

### Phase 1: Core Infrastructure
- [x] Project setup and documentation
- [x] Database schema (Supabase)
- [x] FastAPI backend foundation
- [x] Robot 1: Horizon Scanner

### Phase 2: Data Collection
- [ ] Robot 2: SERP Scraper
- [ ] Robot 3: Metric Analyzer
- [ ] Robot 4: Format Classifier
- [ ] Pipeline integration

### Phase 3: React Dashboard
- [ ] Real-time configuration interface
- [ ] Visual analytics and monitoring
- [ ] Export and reporting features
- [ ] Webhook and integration setup

### Phase 4: Advanced Features
- [ ] Scheduled automated runs
- [ ] Email/Slack notifications
- [ ] Machine learning optimization
- [ ] Multi-user support

## License

MIT License - This is an internal tool for personal use.

## Support

For issues or questions:
1. Check `SUPABASE_SUCCESS.md` for setup details
2. Review `docs/` for additional documentation
3. Check logs in the console or Supabase dashboard

---

Built with modern cloud infrastructure for discovering winning YouTube topics