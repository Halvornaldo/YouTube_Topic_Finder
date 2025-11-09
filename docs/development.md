# Development Guide

Guide for developers working on YouTube Topic Finder.

## Current Development Status

### ✅ Completed (Phase 1)

- [x] Project structure and documentation
- [x] Database schema (9 tables)
- [x] Alembic migrations setup
- [x] FastAPI backend foundation
- [x] Configuration system (YAML-based niches)
- [x] Robot 1: Horizon Scanner
  - [x] Google Trends integration
  - [x] Reddit integration
  - [x] Topic discovery and storage

### 🔜 Next Steps (Phase 2)

- [ ] Robot 2: SERP Scraper
  - [ ] Playwright integration for YouTube scraping
  - [ ] YouTube API fallback
  - [ ] Rate limiting and retry logic
  - [ ] Video metadata extraction

### 🔜 Future Phases

- [ ] Robot 3: Metric Analyzer
- [ ] Robot 4: Format Classifier
- [ ] Full pipeline integration
- [ ] Web UI dashboard
- [ ] Scheduled jobs

## Architecture Overview

### 4-Robot Pipeline

```
┌─────────────────┐
│  Robot 1        │  Discovers seed topics
│  Horizon Scanner│  (Google Trends + Reddit)
└────────┬────────┘
         │ seed_topics table
         ▼
┌─────────────────┐
│  Robot 2        │  Scrapes YouTube search results
│  SERP Scraper   │  (Playwright + API)
└────────┬────────┘
         │ videos table
         ▼
┌─────────────────┐
│  Robot 3        │  Analyzes metrics & opportunity
│  Metric Analyzer│  (YouTube API + Google Ads API)
└────────┬────────┘
         │ video_metrics & opportunity_scores
         ▼
┌─────────────────┐
│  Robot 4        │  Classifies video format
│  Format Class.  │  (Whisper + NLP)
└────────┬────────┘
         │ video_formats
         ▼
    📊 Results
```

## Project Structure

```
YouTube_Topic_Finder/
├── src/
│   ├── api/                    # FastAPI endpoints
│   │   ├── health.py          # Health checks
│   │   ├── robots.py          # Robot control endpoints
│   │   ├── opportunities.py   # Results endpoints
│   │   └── niches.py          # Niche management
│   ├── robots/                # Robot implementations
│   │   ├── horizon_scanner.py ✅
│   │   ├── serp_scraper.py    🔜
│   │   ├── metric_analyzer.py 🔜
│   │   └── format_classifier.py 🔜
│   ├── models/                # SQLAlchemy models (9 tables)
│   ├── services/              # Business logic (future)
│   ├── utils/                 # Helper functions (future)
│   └── config/                # Configuration management
├── migrations/                # Alembic migrations
├── config/niches/            # YAML niche configs
├── tests/                    # Test suite
└── docs/                     # Documentation
```

## Database Schema

### Core Tables

1. **seed_topics** - Topics from Robot 1
2. **videos** - Videos from Robot 2
3. **video_metrics** - Metrics from Robot 3
4. **opportunity_scores** - Scores from Robot 3
5. **video_formats** - Formats from Robot 4

### Supporting Tables

6. **search_queries** - Search tracking
7. **content_gaps** - Identified gaps
8. **niche_configs** - Loaded configs
9. **processing_jobs** - Job queue

## Adding a New Robot

Example: Implementing Robot 2 (SERP Scraper)

### 1. Create Robot Class

```python
# src/robots/serp_scraper.py
class SerpScraper:
    def __init__(self, db_session: Session):
        self.db = db_session

    def run(self, seed_topic_id: int):
        # Implementation
        pass
```

### 2. Update API Endpoint

```python
# src/api/robots.py
@router.post("/serp-scraper/run")
async def run_serp_scraper(request: SerpScrapeRequest, ...):
    from src.robots.serp_scraper import SerpScraper
    scraper = SerpScraper(db)
    # Run in background
    background_tasks.add_task(scraper.run, ...)
```

### 3. Create Tests

```python
# tests/robots/test_serp_scraper.py
def test_serp_scraper():
    # Test implementation
    pass
```

### 4. Update Documentation

- Update `CLAUDE.md` development status
- Update `docs/development.md` progress
- Add usage examples to `README.md`

## Database Migrations

### Creating a New Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Review the generated file in migrations/versions/

# Apply migration
alembic upgrade head
```

### Rolling Back

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback all
alembic downgrade base
```

## Adding a New Niche

### 1. Create YAML Config

```yaml
# config/niches/your_niche.yaml
name: "your_niche"
display_name: "Your Niche Name"
description: "Description"

keywords:
  - "keyword1"
  - "keyword2"

sources:
  google_trends:
    enabled: true
    weight: 0.6
  reddit:
    enabled: true
    weight: 0.4
    subreddits:
      - "subreddit1"
      - "subreddit2"

thresholds:
  min_search_volume: 1000
  max_competition: 0.7
  min_opportunity_score: 60.0

# ... etc
```

### 2. Reload Configurations

```bash
# Via API
curl -X POST http://localhost:8000/api/niches/reload

# Or restart server
```

### 3. Test the Niche

```bash
curl -X POST http://localhost:8000/api/robots/horizon-scanner/run \
  -H "Content-Type: application/json" \
  -d '{"niche": "your_niche", "max_topics": 20}'
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/robots/test_horizon_scanner.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v
```

### Writing Tests

```python
# tests/robots/test_horizon_scanner.py
import pytest
from src.robots.horizon_scanner import HorizonScanner

def test_horizon_scanner_initialization(db_session):
    scanner = HorizonScanner(db_session)
    assert scanner is not None

@pytest.mark.asyncio
async def test_horizon_scanner_run(db_session):
    scanner = HorizonScanner(db_session)
    result = scanner.run("ai_tech", max_topics=5)
    assert result["status"] == "completed"
```

## Code Quality

### Formatting

```bash
# Format code with Black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Check formatting
black --check src/ tests/
```

### Linting

```bash
# Run flake8
flake8 src/ tests/

# Run mypy (type checking)
mypy src/
```

### Pre-commit Checks

```bash
# Run all checks before committing
black src/ tests/ && isort src/ tests/ && flake8 src/ tests/ && pytest
```

## Logging

### Using Logger

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Informational message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)  # Include traceback
```

### Log Levels

Set in `.env`:
```
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Viewing Logs

```bash
# Application logs
tail -f logs/app.log

# Docker logs
docker-compose logs -f postgres
docker-compose logs -f redis
```

## Debugging

### Interactive Debugging

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use IPython debugger
import IPdb; ipdb.set_trace()
```

### Database Inspection

```bash
# Connect to database
docker-compose exec postgres psql -U postgres -d youtube_topic_finder

# List tables
\dt

# Describe table
\d seed_topics

# Query data
SELECT * FROM seed_topics LIMIT 10;
```

### API Testing

```bash
# Using curl
curl -X POST http://localhost:8000/api/robots/horizon-scanner/run \
  -H "Content-Type: application/json" \
  -d '{"niche": "ai_tech"}'

# Using httpx (Python)
import httpx
response = httpx.post("http://localhost:8000/api/robots/horizon-scanner/run",
    json={"niche": "ai_tech"})
```

## Git Workflow

### Branch Naming

- `feature/robot-2-implementation`
- `bugfix/horizon-scanner-rate-limit`
- `docs/setup-guide-improvements`

### Commit Messages

```
feat: Add SERP scraper implementation
fix: Resolve Reddit API rate limiting issue
docs: Update setup guide with API key instructions
refactor: Improve horizon scanner performance
test: Add tests for metric analyzer
```

### Before Committing

1. Run code formatters
2. Run tests
3. Update documentation if needed
4. Check git status

## Performance Optimization

### Database Queries

```python
# Use eager loading for relationships
videos = db.query(Video).options(
    joinedload(Video.metrics),
    joinedload(Video.opportunity_score)
).all()

# Use batch inserts
db.bulk_insert_mappings(SeedTopic, topic_dicts)
```

### Caching

```python
# Use Redis for caching
import redis
r = redis.from_url(settings.REDIS_URL)
r.set("key", "value", ex=3600)  # 1 hour expiry
```

### Async Operations

```python
# Use async for I/O operations
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return response.json()
```

## Security Best Practices

1. **Never commit `.env` file**
2. **Keep API keys secure**
3. **Validate all user inputs**
4. **Use parameterized queries** (SQLAlchemy does this)
5. **Rate limit API endpoints**
6. **Log security events**

## Deployment Checklist

- [ ] Set `DEBUG=false`
- [ ] Use production database
- [ ] Configure CORS properly
- [ ] Set up SSL/TLS
- [ ] Configure logging
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Document deployment process

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **Alembic Docs**: https://alembic.sqlalchemy.org/
- **PyTrends**: https://github.com/GeneralMills/pytrends
- **PRAW**: https://praw.readthedocs.io/

## Questions?

Check `CLAUDE.md` for technical architecture details or review the code comments for inline documentation.
