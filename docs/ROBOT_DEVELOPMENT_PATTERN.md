# Robot Development Pattern

This document outlines the standardized pattern for implementing Robots 2-4, based on the successful implementation of Robot 1 (Horizon Scanner).

## Overview

Each robot follows a consistent architecture integrating with:
- **Configuration System** (Supabase + ConfigManager)
- **Job Tracking** (JobService with SSE events)
- **API Endpoints** (FastAPI with standardized responses)
- **Testing Infrastructure** (Comprehensive API testing before proceeding)

## Development Checklist for Each Robot

### Phase 1: Planning & Design

- [ ] Define robot responsibilities and data flow
- [ ] Design database tables (migrations)
- [ ] Define configuration parameters needed
- [ ] Outline API endpoints required
- [ ] Plan testing strategy

### Phase 2: Core Implementation

**Step 1: Database Models**
- [ ] Create SQLAlchemy models in `src/models/`
- [ ] Generate Alembic migration
- [ ] Test migration on Supabase

**Step 2: Robot Service**
- [ ] Create robot class in `src/robots/{robot_name}.py`
- [ ] Implement `__init__` with ConfigManager integration
- [ ] Implement main processing method
- [ ] Add comprehensive logging
- [ ] Integrate with JobService for tracking

**Step 3: Business Logic Layer**
- [ ] Create service class in `src/services/{robot_name}_service.py`
- [ ] Implement CRUD operations
- [ ] Add validation logic
- [ ] Handle edge cases

**Step 4: API Endpoints**
- [ ] Add endpoints to `src/api/robots.py`
- [ ] Implement trigger endpoint (POST)
- [ ] Add status/results endpoints (GET)
- [ ] Document with proper OpenAPI schemas

### Phase 3: Configuration Integration

**ConfigManager Integration:**
```python
from src/services.config_manager import ConfigManager

class Robot{N}:
    def __init__(self, db_session):
        self.db = db_session
        self.config = ConfigManager(db_session)

    async def run(self, niche_name: str, **overrides):
        # Load niche configuration
        niche_config = self.config.get_niche(niche_name)

        # Get robot-specific settings with fallbacks
        max_items = self.config.get_setting(
            f'ROBOT{N}_MAX_ITEMS',
            default=50,
            niche_name=niche_name
        )

        # Process with config...
```

**Required Settings:**
- `ROBOT{N}_ENABLED` - Enable/disable flag
- `ROBOT{N}_MAX_ITEMS` - Processing limits
- `ROBOT{N}_DELAY_SECONDS` - Rate limiting
- `ROBOT{N}_{SPECIFIC_SETTINGS}` - Robot-specific configs

### Phase 4: Job Tracking Integration

**JobService Integration:**
```python
from src.services.job_service import JobService, JobType

async def run(self, niche_name: str):
    job_service = JobService(self.db)

    # Create job
    job = job_service.create_job(
        job_type=JobType.ROBOT{N},
        niche_name=niche_name,
        parameters={'custom': 'params'}
    )

    try:
        # Update progress
        job_service.update_job(job.id,
            status='running',
            current_step='Processing...',
            progress=0.25
        )

        # Process...
        results = await self.process()

        # Complete
        job_service.complete_job(job.id, results)

    except Exception as e:
        job_service.fail_job(job.id, str(e))
        raise
```

### Phase 5: API Implementation Pattern

**Endpoint Structure (in `src/api/robots.py`):**
```python
@router.post("/robot{n}/run", response_model=Robot{N}Response)
async def run_robot{n}(
    request: Robot{N}Request,
    db: Session = Depends(get_db)
):
    """
    Trigger Robot {N} - {Description}.

    Args:
        request: Contains niche_name and optional overrides
        db: Database session

    Returns:
        Job information and initial results
    """
    try:
        robot = Robot{N}(db)
        result = await robot.run(
            niche_name=request.niche_name,
            **request.dict(exclude={'niche_name'})
        )

        return Robot{N}Response(
            success=True,
            job_id=result['job_id'],
            message=f"Robot {N} started successfully",
            data=result
        )

    except Exception as e:
        logger.error(f"Robot {N} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Phase 6: Testing (MANDATORY)

Before proceeding to next robot, test thoroughly:

**API Testing:**
```bash
# 1. Test robot trigger
curl -X POST http://localhost:8000/api/robots/robot{n}/run \
  -H "Content-Type: application/json" \
  -d '{"niche_name":"ai_tech"}'

# 2. Monitor job progress
curl http://localhost:8000/api/jobs/{job_id}

# 3. Verify results in database
```

**Database Testing:**
- [ ] Verify data is saved correctly
- [ ] Check foreign key relationships
- [ ] Validate data integrity

**Configuration Testing:**
- [ ] Test with different niches
- [ ] Verify settings override
- [ ] Test hot-reload (if applicable)

**Error Handling Testing:**
- [ ] Test API failures
- [ ] Test database errors
- [ ] Test timeout scenarios

## Robot 1 Reference Implementation

**Robot 1 (Horizon Scanner)** serves as the reference:

### What Works Well:
- ConfigManager integration with niche-specific overrides
- JobService tracking with progress updates
- SSE event streaming for real-time updates
- Comprehensive error handling
- Reddit API integration with rate limiting
- CSV export functionality

### Files to Reference:
- `src/robots/horizon_scanner.py` - Main robot implementation
- `src/api/robots.py` (horizon-scanner endpoints) - API pattern
- `src/services/config_manager.py` - Configuration integration
- `src/services/job_service.py` - Job tracking pattern

## Robot-Specific Considerations

### Robot 2 (SERP Scraper)
**Unique Requirements:**
- Playwright browser automation
- YouTube API fallback logic
- Rate limiting for scraping
- Screenshot capture (optional)
- Proxy rotation (if needed)

**Configuration Needed:**
- `ROBOT2_USE_PLAYWRIGHT` - Toggle browser automation
- `ROBOT2_HEADLESS` - Browser mode
- `ROBOT2_MAX_VIDEOS_PER_QUERY` - Scraping limit
- `ROBOT2_YOUTUBE_API_FALLBACK` - Enable API fallback

### Robot 3 (Metric Analyzer)
**Unique Requirements:**
- YouTube Data API v3 integration
- Google Ads API integration
- Sentiment analysis
- View velocity calculations

**Configuration Needed:**
- `ROBOT3_YOUTUBE_API_KEY` - API key
- `ROBOT3_GOOGLE_ADS_TOKEN` - Ads API token
- `ROBOT3_SENTIMENT_THRESHOLD` - Minimum sentiment score
- `ROBOT3_MIN_VIEWS_FOR_VELOCITY` - Velocity calc threshold

### Robot 4 (Format Classifier)
**Unique Requirements:**
- Audio download (pytube)
- OpenAI Whisper transcription
- NLP analysis
- Format classification ML model

**Configuration Needed:**
- `ROBOT4_OPENAI_API_KEY` - Whisper API key
- `ROBOT4_MAX_AUDIO_LENGTH_SECONDS` - Processing limit
- `ROBOT4_CONFIDENCE_THRESHOLD` - Min confidence for classification
- `ROBOT4_SUPPORTED_FORMATS` - List of video formats

## Integration Testing

After all 4 robots are implemented:

### Full Pipeline Test:
```bash
# 1. Trigger full pipeline
curl -X POST http://localhost:8000/api/robots/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"niche_name":"ai_tech"}'

# 2. Monitor via SSE
curl -N http://localhost:8000/api/events/stream

# 3. Verify end-to-end flow
# Robot 1 → seed_topics
# Robot 2 → videos
# Robot 3 → video_metrics + opportunity_scores
# Robot 4 → video_formats
```

## Documentation Requirements

For each robot, update:
- [ ] CLAUDE.md - Overall progress
- [ ] README.md - Usage examples
- [ ] API documentation - OpenAPI schemas
- [ ] This document - Lessons learned

## Commit Strategy

After each robot completion:
```bash
# 1. Run tests
pytest tests/robots/test_robot{n}.py

# 2. Stage changes
git add src/robots/robot{n}.py
git add src/api/robots.py
git add migrations/versions/{migration_file}.py
git add docs/

# 3. Commit with descriptive message
git commit -m "feat: Implement Robot {N} - {Description}

- Add {robot_name} core functionality
- Integrate with ConfigManager and JobService
- Add API endpoints and testing
- Update documentation

Tested: {list key test scenarios}"

# 4. Push to branch
git push origin {branch_name}
```

## Success Criteria

Robot is considered complete when:
- ✅ All Phase 1-6 checklist items completed
- ✅ API endpoints returning 200 OK
- ✅ Data saving correctly to Supabase
- ✅ Job tracking working with progress updates
- ✅ SSE events streaming for real-time updates
- ✅ Configuration integration functional
- ✅ Error handling robust
- ✅ Documentation updated
- ✅ Committed to git with tests passing

## Key Principles

1. **Incremental Development** - One robot at a time
2. **Test Before Proceeding** - No moving forward with broken code
3. **Configuration First** - Everything configurable from dashboard
4. **Real-time Updates** - SSE for all long-running operations
5. **Error Transparency** - Clear error messages, comprehensive logging
6. **Database-First** - All config in Supabase, YAML just templates
7. **Async/Await** - All I/O operations non-blocking
8. **Type Safety** - Pydantic models for all data structures

---

**Last Updated:** 2025-11-11
**Pattern Based On:** Robot 1 (Horizon Scanner) successful implementation
