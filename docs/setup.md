# Setup Guide - YouTube Topic Finder

Complete setup instructions for the YouTube Topic Finder project.

## Prerequisites

- **Python 3.11+** (recommended 3.11 or 3.12)
- **Docker & Docker Compose** (for PostgreSQL and Redis)
- **Git** (for version control)

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd YouTube_Topic_Finder
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt
```

**Note for Robot 4 (Whisper):** If you encounter issues with PyTorch/Whisper installation, install CPU-only version:

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 4. Set Up Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
# Use your favorite editor (nano, vim, VSCode, etc.)
nano .env
```

**Required API Keys:**

1. **Reddit API** (Required for Robot 1):
   - Go to https://www.reddit.com/prefs/apps
   - Create a new app (script type)
   - Copy Client ID and Secret to `.env`

2. **YouTube Data API v3** (Required for Robot 2 & 3):
   - Go to https://console.cloud.google.com/apis/credentials
   - Create project and enable YouTube Data API v3
   - Create API key and copy to `.env`

3. **OpenAI API** (Required for Robot 4):
   - Go to https://platform.openai.com/api-keys
   - Create API key and copy to `.env`

4. **Google Ads API** (Optional for Robot 3):
   - Follow https://developers.google.com/google-ads/api/docs/first-call/overview
   - Add credentials to `.env`

### 5. Start Infrastructure (PostgreSQL + Redis)

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Verify containers are running
docker-compose ps

# Check logs if needed
docker-compose logs postgres
docker-compose logs redis
```

**Optional GUI Tools:**

```bash
# Start PgAdmin (PostgreSQL GUI) - http://localhost:5050
docker-compose --profile tools up -d pgadmin

# Start Redis Commander - http://localhost:8081
docker-compose --profile tools up -d redis-commander
```

### 6. Initialize Database

```bash
# Run database migrations
alembic upgrade head

# Verify tables were created
docker-compose exec postgres psql -U postgres -d youtube_topic_finder -c "\dt"
```

You should see 9 tables:
- seed_topics
- videos
- video_metrics
- opportunity_scores
- video_formats
- search_queries
- content_gaps
- niche_configs
- processing_jobs

### 7. Start FastAPI Server

```bash
# Development mode (auto-reload)
uvicorn src.main:app --reload --port 8000

# Or using Python directly
python -m src.main
```

The server will start at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 8. Verify Setup

```bash
# Check health endpoint
curl http://localhost:8000/api/health

# List available niches
curl http://localhost:8000/api/niches/

# Test ping
curl http://localhost:8000/api/ping
```

Expected health check response:
```json
{
  "status": "healthy",
  "app": "YouTube Topic Finder",
  "version": "1.0.0",
  "database": "healthy",
  "redis": "healthy"
}
```

## Running Robot 1 (Horizon Scanner)

Once setup is complete, test Robot 1:

```bash
# Run Horizon Scanner for AI/Tech niche
curl -X POST http://localhost:8000/api/robots/horizon-scanner/run \
  -H "Content-Type: application/json" \
  -d '{"niche": "ai_tech", "max_topics": 20}'
```

Check the logs to see topics being discovered!

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis connection
redis-cli ping

# Restart Redis
docker-compose restart redis
```

### Python Package Issues

```bash
# Clear pip cache
pip cache purge

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### Port Already in Use

If port 8000, 5432, or 6379 is already in use:

1. Stop conflicting services
2. Or modify ports in `docker-compose.yml` and `.env`

### API Key Issues

Verify API keys are correctly set in `.env`:

```bash
# Check environment variables are loaded
python -c "from src.config.settings import settings; print(settings.REDDIT_CLIENT_ID)"
```

## Next Steps

After setup is complete:

1. **Test Robot 1**: Run horizon scanner for different niches
2. **Review Data**: Check database for discovered topics
3. **Customize Niches**: Edit YAML configs in `config/niches/`
4. **Prepare for Robot 2**: Ensure YouTube API key is configured

## Development Workflow

```bash
# 1. Pull latest changes
git pull

# 2. Update dependencies if needed
pip install -r requirements.txt

# 3. Run migrations
alembic upgrade head

# 4. Start server
uvicorn src.main:app --reload
```

## Production Deployment

For production deployment:

1. Set `DEBUG=false` in `.env`
2. Use proper database credentials
3. Configure CORS properly in `src/main.py`
4. Use production-grade ASGI server (Gunicorn + Uvicorn workers)
5. Set up reverse proxy (Nginx)
6. Enable SSL/TLS
7. Set up monitoring and logging

## Resources

- **API Documentation**: http://localhost:8000/docs
- **Project Documentation**: See `/docs` directory
- **Technical Blueprint**: See `CLAUDE.md`
- **User Guide**: See `README.md`

## Support

For issues:
1. Check logs in `logs/` directory
2. Review `CLAUDE.md` for technical details
3. Check database state with PgAdmin
4. Verify API keys are valid and have proper quotas
