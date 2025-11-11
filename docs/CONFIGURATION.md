# Configuration System Guide

## Overview

The YouTube Topic Finder is designed to be **fully configurable** from a React dashboard without requiring code changes or server restarts (for most settings). This guide explains the configuration architecture, API endpoints, and best practices.

## Configuration Philosophy

### Database-First Approach

**Primary Storage: Supabase PostgreSQL**
- All active configurations stored in database
- User-created niches, settings, and preferences
- Full version history and audit trail
- Real-time updates to React dashboard

**Template System: YAML Files**
- Read-only example configurations
- Shipped with the application in `config/templates/niches/`
- Loaded into database on first startup
- Can be cloned to create custom configurations

**Sync Strategy:**
- One-way: YAML templates → Database (on startup)
- Database is the single source of truth
- Changes from dashboard saved directly to database
- No automatic YAML file updates

### Incremental Development

Configuration infrastructure is built alongside each robot:
- ✅ **Robot 1** (Horizon Scanner): Full config support
- 🔜 **Robot 2** (SERP Scraper): Config added when robot is built
- 🔜 **Robot 3** (Metric Analyzer): Config added when robot is built
- 🔜 **Robot 4** (Format Classifier): Config added when robot is built

This ensures configuration APIs evolve with the system's needs.

## Configuration Tables

### app_settings

Stores all application settings with hot-reload support.

**Schema:**
```sql
CREATE TABLE app_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(200) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    category VARCHAR(100),  -- 'robot1', 'robot2', 'processing', 'api_keys', etc.
    data_type VARCHAR(50),  -- 'string', 'integer', 'boolean', 'json'
    requires_restart BOOLEAN DEFAULT false,
    description TEXT,
    default_value TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Example Entries:**
```json
{
  "key": "ROBOT1_MAX_TOPICS_PER_RUN",
  "value": "20",
  "category": "robot1",
  "data_type": "integer",
  "requires_restart": false,
  "description": "Maximum number of topics to discover in one run"
}
```

### niche_configs

User-created and template niche configurations.

**Schema:**
```sql
CREATE TABLE niche_configs (
    id SERIAL PRIMARY KEY,
    niche_name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    description TEXT,
    keywords JSON NOT NULL,  -- Array of keywords
    seed_topics JSON,        -- Optional predefined topics
    google_trends_enabled INTEGER DEFAULT 1,
    google_trends_weight FLOAT DEFAULT 0.5,
    reddit_enabled INTEGER DEFAULT 1,
    reddit_weight FLOAT DEFAULT 0.5,
    reddit_subreddits JSON,  -- Array of subreddit names
    min_search_volume INTEGER,
    max_competition FLOAT,
    min_opportunity_score FLOAT,
    preferred_formats JSON,  -- Array of format types
    target_regions JSON,     -- Array of region codes
    is_template BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(100),  -- 'system', 'user', or user ID
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### job_status

Real-time job tracking for monitoring.

**Schema:**
```sql
CREATE TABLE job_status (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(100) NOT NULL,  -- 'horizon_scan', 'serp_scrape', etc.
    status VARCHAR(50) NOT NULL,     -- 'pending', 'running', 'completed', 'failed'
    progress_percent INTEGER DEFAULT 0,
    current_step VARCHAR(200),
    total_steps INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    result_summary JSON,             -- Stats about what was found
    config_snapshot JSON,            -- Configuration used for this job
    created_at TIMESTAMP DEFAULT NOW()
);
```

### config_history

Version control for all configuration changes.

**Schema:**
```sql
CREATE TABLE config_history (
    id SERIAL PRIMARY KEY,
    config_type VARCHAR(100) NOT NULL,  -- 'niche', 'setting', 'robot_param'
    config_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    changes_json JSON NOT NULL,  -- Diff of what changed
    changed_by VARCHAR(100),     -- User ID or 'system'
    changed_at TIMESTAMP DEFAULT NOW(),
    rollback_available BOOLEAN DEFAULT true
);
```

## API Endpoints

### Niche Management

**List all niches:**
```bash
GET /api/niches/
Response: {"niches": [...], "default": "ai_tech"}
```

**Get niche details:**
```bash
GET /api/niches/{id}
Response: {niche configuration object}
```

**Create new niche:**
```bash
POST /api/niches/
Body: {
  "name": "custom_niche",
  "display_name": "My Custom Niche",
  "keywords": ["topic1", "topic2"],
  "reddit_subreddits": ["sub1", "sub2"],
  ...
}
```

**Update niche:**
```bash
PUT /api/niches/{id}
Body: {fields to update}
```

**Delete niche:**
```bash
DELETE /api/niches/{id}
```

**Test niche configuration:**
```bash
POST /api/niches/{id}/test
Response: {
  "reddit_valid": true,
  "subreddits_accessible": ["sub1", "sub2"],
  "estimated_topics": 45
}
```

**Clone niche:**
```bash
POST /api/niches/{id}/clone
Body: {"new_name": "cloned_niche"}
```

**Import niches:**
```bash
POST /api/niches/import
Body: {
  "format": "json",  // or "yaml"
  "data": "..."
}
```

**Export all niches:**
```bash
GET /api/niches/export/all?format=json
# or ?format=yaml
```

### Settings Management

**Get all settings:**
```bash
GET /api/settings
Response: {
  "robot1": {...},
  "robot2": {...},
  "processing": {...},
  "api_keys": {...}
}
```

**Get settings by category:**
```bash
GET /api/settings/robot1
Response: {
  "ROBOT1_MAX_TOPICS_PER_RUN": 20,
  "ROBOT1_REDDIT_ENABLED": true,
  ...
}
```

**Get settings schema:**
```bash
GET /api/settings/schema
Response: {
  "ROBOT1_MAX_TOPICS_PER_RUN": {
    "type": "integer",
    "min": 1,
    "max": 100,
    "requires_restart": false,
    "description": "..."
  },
  ...
}
```

**Update single setting:**
```bash
PATCH /api/settings/ROBOT1_MAX_TOPICS_PER_RUN
Body: {"value": 30}
Response: {"requires_restart": false}
```

**Bulk update settings:**
```bash
PUT /api/settings
Body: {
  "ROBOT1_MAX_TOPICS_PER_RUN": 30,
  "ROBOT1_REDDIT_ENABLED": false
}
Response: {
  "updated": ["ROBOT1_MAX_TOPICS_PER_RUN", "ROBOT1_REDDIT_ENABLED"],
  "requires_restart": false
}
```

**Hot-reload settings:**
```bash
POST /api/settings/reload
Response: {
  "reloaded": ["ROBOT1_MAX_TOPICS_PER_RUN"],
  "requires_restart": ["YOUTUBE_API_KEY"]
}
```

### Job Monitoring

**List recent jobs:**
```bash
GET /api/jobs?status=running&limit=10
Response: {"jobs": [...]}
```

**Get job details:**
```bash
GET /api/jobs/{id}
Response: {
  "id": 123,
  "job_type": "horizon_scan",
  "status": "running",
  "progress_percent": 45,
  "current_step": "Scanning Reddit r/MachineLearning",
  ...
}
```

**Cancel running job:**
```bash
DELETE /api/jobs/{id}
```

**Retry failed job:**
```bash
POST /api/jobs/{id}/retry
```

### Validation & Testing

**Validate niche config:**
```bash
POST /api/validate/niche
Body: {niche configuration object}
Response: {
  "valid": true,
  "errors": [],
  "warnings": ["Subreddit 'xyz' may be private"]
}
```

**Test Reddit API:**
```bash
POST /api/validate/reddit
Body: {
  "client_id": "...",
  "client_secret": "...",
  "subreddits": ["artificial", "MachineLearning"]
}
Response: {
  "connection_valid": true,
  "accessible_subreddits": ["artificial", "MachineLearning"],
  "inaccessible_subreddits": []
}
```

**Test API keys:**
```bash
POST /api/validate/api-key
Body: {
  "api_type": "youtube",  // or "openai", "google_ads"
  "api_key": "..."
}
Response: {
  "valid": true,
  "quota_remaining": 9500,
  "rate_limit": "10,000 units/day"
}
```

**Validate all settings:**
```bash
GET /api/validate/settings
Response: {
  "valid": true,
  "incompatible_settings": [],
  "missing_required": []
}
```

### Real-time Events (Server-Sent Events)

**Stream job progress:**
```bash
GET /api/events/jobs/{id}
# Server sends events:
event: progress
data: {"percent": 45, "step": "Scanning Reddit"}

event: completed
data: {"topics_found": 20, "duration": 45}
```

**Stream new discoveries:**
```bash
GET /api/events/discoveries
# Server sends events when new topics found:
event: new_topic
data: {"id": 123, "title": "...", "source": "reddit"}
```

**Stream robot status:**
```bash
GET /api/events/robots
# Server sends events on robot state changes:
event: robot_started
data: {"robot": "horizon_scanner", "job_id": 123}

event: robot_completed
data: {"robot": "horizon_scanner", "job_id": 123, "status": "success"}
```

## Hot-reload vs Restart

### Hot-reloadable Settings

These settings can be changed without restarting the server:

**Robot Behavior:**
- `ROBOT1_MAX_TOPICS_PER_RUN`
- `ROBOT1_REDDIT_ENABLED`
- `ROBOT1_GOOGLE_TRENDS_ENABLED`
- `ROBOT2_MAX_VIDEOS_PER_QUERY`
- `ROBOT2_REQUEST_DELAY_SECONDS`
- `ROBOT3_BATCH_SIZE`
- `ROBOT4_WHISPER_MODEL`

**Niche Configurations:**
- All niche settings (keywords, subreddits, thresholds)

**Processing Limits:**
- `MAX_CONCURRENT_JOBS`
- `JOB_TIMEOUT_SECONDS`

**Scoring Thresholds:**
- `min_opportunity_score`
- `min_search_volume`
- `max_competition`

### Requires Restart

These settings require server restart for security or architectural reasons:

**Infrastructure:**
- `DATABASE_URL`
- `REDIS_URL`
- `REDIS_MAX_CONNECTIONS`

**API Keys (encrypted):**
- `YOUTUBE_API_KEY`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `OPENAI_API_KEY`
- `GOOGLE_ADS_DEVELOPER_TOKEN`

**Application Settings:**
- `APP_NAME`
- `DEBUG`
- `LOG_LEVEL`

## Using the Configuration System

### From React Dashboard (Planned)

**1. View Current Configuration:**
```javascript
// Fetch all niches
const niches = await fetch('/api/niches/').then(r => r.json());

// Fetch robot settings
const robot1Settings = await fetch('/api/settings/robot1').then(r => r.json());
```

**2. Create New Niche:**
```javascript
const newNiche = {
  name: "tech_startups",
  display_name: "Tech Startups",
  keywords: ["startup", "founder", "venture capital"],
  reddit_subreddits: ["startups", "Entrepreneur"],
  min_opportunity_score: 70
};

const response = await fetch('/api/niches/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(newNiche)
});
```

**3. Update Setting with Hot-reload:**
```javascript
const response = await fetch('/api/settings/ROBOT1_MAX_TOPICS_PER_RUN', {
  method: 'PATCH',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({value: 30})
});

if (response.requires_restart) {
  alert('Server restart required for this change');
} else {
  alert('Setting updated immediately!');
}
```

**4. Monitor Job Progress:**
```javascript
const eventSource = new EventSource('/api/events/jobs/123');

eventSource.addEventListener('progress', (e) => {
  const data = JSON.parse(e.data);
  updateProgressBar(data.percent);
  updateStatus(data.step);
});

eventSource.addEventListener('completed', (e) => {
  const data = JSON.parse(e.data);
  showResults(data);
  eventSource.close();
});
```

**5. Test Before Saving:**
```javascript
const testResult = await fetch('/api/validate/niche', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(nicheConfig)
});

if (testResult.valid) {
  // Save the niche
  await saveNiche(nicheConfig);
} else {
  showErrors(testResult.errors);
}
```

### From Command Line (Development)

**1. Update a setting:**
```bash
curl -X PATCH http://localhost:8000/api/settings/ROBOT1_MAX_TOPICS_PER_RUN \
  -H "Content-Type: application/json" \
  -d '{"value": 30}'
```

**2. Create a niche from JSON:**
```bash
cat my_niche.json | curl -X POST http://localhost:8000/api/niches/ \
  -H "Content-Type: application/json" \
  -d @-
```

**3. Test Reddit connection:**
```bash
curl -X POST http://localhost:8000/api/validate/reddit \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "your_id",
    "client_secret": "your_secret",
    "subreddits": ["artificial"]
  }'
```

**4. Monitor job with curl:**
```bash
curl -N http://localhost:8000/api/events/jobs/123
```

## YAML Templates

### Template Structure

Templates are stored in `config/templates/niches/` and follow this structure:

```yaml
# Basic info
name: "ai_tech"
display_name: "AI & Technology"
description: "Artificial Intelligence and emerging tech topics"

# Discovery keywords
keywords:
  - "artificial intelligence"
  - "machine learning"
  - "AI tools"

# Optional seed topics
seed_topics:
  - "AI video generators"
  - "ChatGPT alternatives"

# Data sources
sources:
  google_trends:
    enabled: true
    weight: 0.6
    region: "US"
    timeframe: "now 7-d"

  reddit:
    enabled: true
    weight: 0.4
    subreddits:
      - "artificial"
      - "MachineLearning"
    min_upvotes: 50
    time_filter: "week"

# Scoring thresholds
thresholds:
  min_search_volume: 1000
  max_competition: 0.7
  min_opportunity_score: 60.0

# Format preferences
formats:
  preferred:
    - "tutorial"
    - "comparison"
  excluded:
    - "vlog"

# Regional targeting
regional:
  target_regions:
    - "US"
    - "GB"
  target_languages:
    - "en"

# Custom settings
custom:
  focus_on_tools: true
  include_news: true
```

### Loading Templates

Templates are automatically loaded into the database on first startup:

1. Application reads all `.yaml` files from `config/templates/niches/`
2. Parses YAML into niche configuration objects
3. Inserts into `niche_configs` table with `is_template=true`
4. Users can then clone templates to create custom niches

### Cloning Templates

From dashboard:
```javascript
// Clone the ai_tech template
const response = await fetch('/api/niches/1/clone', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({new_name: "my_ai_niche"})
});
```

The cloned niche will have `is_template=false` and can be edited freely.

## Best Practices

### Configuration Management

1. **Test before deploying**: Always use validation endpoints before saving
2. **Version control**: Database automatically tracks configuration history
3. **Use templates**: Clone templates instead of creating from scratch
4. **Document changes**: Use descriptive commit messages in config_history

### Hot-reload Strategy

1. **Check restart flag**: Always check `requires_restart` in responses
2. **Batch updates**: Use bulk update endpoint to change multiple settings at once
3. **Reload after batch**: Call `/api/settings/reload` after bulk updates
4. **Monitor effects**: Watch job performance after configuration changes

### Niche Configuration

1. **Start with templates**: Clone existing niches that are similar
2. **Test subreddits**: Use `/api/validate/reddit` to verify subreddit access
3. **Iterate on thresholds**: Start conservative, adjust based on results
4. **Monitor results**: Track which niches produce best opportunities

### Job Monitoring

1. **Use SSE for real-time**: Connect to event streams for active jobs
2. **Poll for history**: Use REST endpoints for completed jobs
3. **Set appropriate timeouts**: Configure `JOB_TIMEOUT_SECONDS` based on niche complexity
4. **Track failures**: Monitor failed jobs and adjust configurations

## Troubleshooting

### Configuration Not Applied

**Problem**: Changed a setting but robot still uses old value

**Solutions:**
1. Check if setting `requires_restart` - may need server restart
2. Call `/api/settings/reload` to force hot-reload
3. Verify setting was saved: `GET /api/settings/{key}`
4. Check logs for reload errors

### Validation Failing

**Problem**: Niche validation returns errors

**Common Issues:**
1. **Subreddit not accessible**: Check if subreddit exists and is public
2. **Invalid keywords**: Ensure keywords are non-empty strings
3. **Threshold conflicts**: `min_opportunity_score` can't be > 100
4. **Missing required fields**: `keywords` and `name` are required

### Job Not Starting

**Problem**: Robot job stays in "pending" status

**Check:**
1. **Concurrent limit**: May have hit `MAX_CONCURRENT_JOBS`
2. **API keys**: Verify Reddit/YouTube credentials are valid
3. **Niche active**: Ensure niche has `is_active=true`
4. **System resources**: Check Redis and database connections

### SSE Connection Issues

**Problem**: Real-time events not streaming

**Solutions:**
1. **Browser support**: Ensure browser supports Server-Sent Events
2. **CORS**: Verify CORS headers allow event connections
3. **Network**: Check for proxies blocking SSE
4. **Fallback**: Use polling as fallback for incompatible clients

## Security Considerations

### API Keys

- Stored encrypted in `app_settings` table
- Never exposed in API responses
- Require server restart to change (security measure)
- Validation endpoint tests without exposing key

### Configuration Changes

- All changes logged in `config_history`
- Track who made changes (`changed_by`)
- Rollback capability for accidental changes
- Rate limiting on configuration endpoints (future)

### Validation

- All inputs validated against Pydantic schemas
- SQL injection prevention via parameterized queries
- XSS prevention in dashboard (future)
- API authentication required (future)

## Future Enhancements

### Planned Features

- **User authentication**: Multi-user support with role-based access
- **Configuration presets**: Save and load complete system states
- **A/B testing**: Run multiple configurations and compare results
- **Auto-tuning**: ML-based configuration optimization
- **Webhooks**: Trigger external actions on configuration changes
- **Audit log**: Detailed tracking of all system changes
- **Import/export UI**: Drag-and-drop configuration management
- **Template marketplace**: Share niches with community

## Support

For issues with the configuration system:
1. Check API documentation: http://localhost:8000/docs
2. Review logs in console
3. Consult this guide
4. Check `docs/` for additional documentation
