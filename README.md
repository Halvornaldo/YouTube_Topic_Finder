# YouTube Topic Finder

An automated YouTube topic discovery tool that identifies high-opportunity content ideas using a 4-robot microservice architecture.

## Overview

YouTube Topic Finder analyzes trending topics across multiple platforms, scrapes video performance data, calculates opportunity scores, and predicts winning video formats - all to generate AI-ready content prompts.

## Features

- **🔍 Multi-Source Discovery**: Scans Google Trends and Reddit for emerging topics
- **📊 Smart Scraping**: Hybrid Playwright + API approach for reliable data collection
- **💯 Opportunity Scoring**: Multi-factor analysis (search volume, competition, velocity, sentiment)
- **🎯 Format Prediction**: AI-powered video format classification from transcripts
- **🎨 Content Gap Analysis**: Identifies underserved market opportunities
- **⚙️ Customizable Niches**: YAML-based configuration for different content categories

## Architecture

### 4-Robot System

1. **Horizon Scanner**: Discovers trending seed topics (Google Trends + Reddit)
2. **SERP Scraper**: Scrapes YouTube search results (Playwright + API fallback)
3. **Metric Analyzer**: Calculates opportunity scores (YouTube Data API + Google Ads API)
4. **Format Classifier**: Predicts video formats (Whisper transcription + NLP analysis)

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+
- **Queue**: Redis 7+
- **APIs**: YouTube Data API v3, Google Ads API, OpenAI Whisper
- **Scraping**: Playwright
- **Audio**: pytube

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- API keys (YouTube, Reddit, OpenAI)

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd YouTube_Topic_Finder

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Start infrastructure
docker-compose up -d

# 6. Run database migrations
alembic upgrade head

# 7. Start the server
uvicorn src.main:app --reload --port 8000
```

### Configuration

Edit niche configurations in `config/niches/`:

```yaml
# config/niches/ai_tech.yaml
name: "AI & Technology"
keywords:
  - "artificial intelligence"
  - "machine learning"
  - "AI tools"
sources:
  google_trends:
    enabled: true
    weight: 0.6
  reddit:
    enabled: true
    weight: 0.4
    subreddits:
      - "artificial"
      - "MachineLearning"
```

## Usage

### Run Individual Robots

```bash
# Robot 1: Horizon Scanner
curl -X POST http://localhost:8000/api/robots/horizon-scanner/run \
  -H "Content-Type: application/json" \
  -d '{"niche": "ai_tech"}'

# Robot 2: SERP Scraper
curl -X POST http://localhost:8000/api/robots/serp-scraper/run \
  -H "Content-Type: application/json" \
  -d '{"topic_id": 1}'

# Robot 3: Metric Analyzer
curl -X POST http://localhost:8000/api/robots/metric-analyzer/run \
  -H "Content-Type: application/json" \
  -d '{"video_ids": [1, 2, 3]}'

# Robot 4: Format Classifier
curl -X POST http://localhost:8000/api/robots/format-classifier/run \
  -H "Content-Type: application/json" \
  -d '{"video_id": 1}'
```

### Run Full Pipeline

```bash
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"niche": "ai_tech", "max_topics": 10}'
```

### Get Results

```bash
# Get top opportunities
curl http://localhost:8000/api/opportunities?limit=10

# Get specific topic analysis
curl http://localhost:8000/api/topics/1/analysis
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

9-table schema tracking the full pipeline:

- `seed_topics` - Trending topics discovered by Robot 1
- `videos` - Candidate videos from Robot 2
- `video_metrics` - Raw performance metrics from Robot 3
- `opportunity_scores` - Calculated opportunity scores
- `video_formats` - Format predictions from Robot 4
- `search_queries` - Search tracking
- `content_gaps` - Identified gaps
- `niche_configs` - Loaded configurations
- `processing_jobs` - Job queue

## Development

### Project Structure

```
YouTube_Topic_Finder/
├── src/
│   ├── api/              # FastAPI routes
│   ├── robots/           # 4 robot implementations
│   ├── models/           # Database models
│   ├── services/         # Business logic
│   ├── utils/            # Utilities
│   └── config/           # Config management
├── migrations/           # Database migrations
├── config/              # YAML configs
├── tests/               # Tests
└── docs/                # Documentation
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

### Adding a New Niche

1. Create YAML config in `config/niches/your_niche.yaml`
2. Define keywords, sources, and thresholds
3. Restart the server to load the config

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Troubleshooting

### Common Issues

**Database connection errors:**
```bash
# Check if PostgreSQL is running
docker-compose ps

# View logs
docker-compose logs postgres
```

**Redis connection errors:**
```bash
# Check Redis status
docker-compose ps redis

# Test connection
redis-cli ping
```

**API rate limiting:**
- YouTube API: 10,000 units/day (check quota in Google Console)
- Reddit API: 60 requests/minute (adjust delay in config)

## Roadmap

- [x] Robot 1: Horizon Scanner
- [ ] Robot 2: SERP Scraper
- [ ] Robot 3: Metric Analyzer
- [ ] Robot 4: Format Classifier
- [ ] Web UI dashboard
- [ ] Scheduled automated runs
- [ ] Email/Slack notifications
- [ ] Export to CSV/Excel

## License

MIT License - This is an internal tool for personal use.

## Support

For issues or questions:
1. Check `CLAUDE.md` for technical details
2. Review `docs/` for additional documentation
3. Check logs in `logs/` directory

---

Built with ❤️ for discovering winning YouTube topics
