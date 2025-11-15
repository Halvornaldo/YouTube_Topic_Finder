# How to Change the Gemini LLM Model

Robot 1.5 uses Google Gemini for topic scoring. The model is **hot-swappable** - you can change it without restarting the server!

## Current Model

Check which model is currently configured:
```bash
curl http://localhost:8000/api/settings/robot1_5_llm_model
```

Default: `gemini-2.0-flash-exp`

## Available Models

| Model | Speed | Quality | Cost | Best For |
|-------|-------|---------|------|----------|
| **gemini-2.0-flash-exp** | ⚡⚡⚡ Fastest | ⭐⭐⭐ Good | 💰 Cheapest | **Default - Testing & Development** |
| **gemini-1.5-flash** | ⚡⚡ Fast | ⭐⭐⭐ Good | 💰💰 Low | **Recommended for Production** |
| **gemini-1.5-pro** | ⚡ Slower | ⭐⭐⭐⭐⭐ Excellent | 💰💰💰💰 High | High-Quality Scoring (overkill) |
| **gemini-1.0-pro** | ⚡⚡ Fast | ⭐⭐ Basic | 💰 Low | Not recommended |

## How to Change (3 Ways)

### Method 1: API (Recommended - Hot Swap)

Change model **without restarting** the server:

```bash
# Switch to production-stable model
curl -X PUT http://localhost:8000/api/settings/robot1_5_llm_model \
  -H "Content-Type: application/json" \
  -d '{"value": "gemini-1.5-flash"}'

# Switch to highest quality model
curl -X PUT http://localhost:8000/api/settings/robot1_5_llm_model \
  -H "Content-Type: application/json" \
  -d '{"value": "gemini-1.5-pro"}'

# Switch back to experimental model
curl -X PUT http://localhost:8000/api/settings/robot1_5_llm_model \
  -H "Content-Type: application/json" \
  -d '{"value": "gemini-2.0-flash-exp"}'
```

The next time Robot 1.5 runs, it will use the new model!

### Method 2: Database Script

```bash
python scripts/add_llm_model_config.py  # If not already run
# Then manually update the value in the database
```

### Method 3: Environment Variable

Add to `.env`:
```bash
ROBOT1_5_LLM_MODEL=gemini-1.5-flash
```

Then restart the server.

## Verify the Change

Run Robot 1.5 and check the logs:

```bash
curl -X POST http://localhost:8000/api/robots/topic-scorer/run \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 1}'
```

**Expected log output:**
```
LLM service initialized with model: gemini-1.5-flash
```

## Model Recommendations

### For Testing & Development
✅ **Use `gemini-2.0-flash-exp`** (default)
- Fastest responses (~3 seconds/topic)
- Cheapest ($0.015 per 1M tokens)
- Latest experimental features

### For Production
✅ **Use `gemini-1.5-flash`**
- Stable and reliable
- Fast enough for production
- Good balance of speed/cost/quality

### For Maximum Quality
⚠️ **Use `gemini-1.5-pro`** (only if needed)
- Best reasoning capabilities
- 4x more expensive than flash
- Slower responses
- Probably overkill for topic scoring

## Cost Comparison

For scoring **1000 topics**:

| Model | Estimated Cost | Response Time |
|-------|---------------|---------------|
| gemini-2.0-flash-exp | ~$0.30 | ~50 minutes |
| gemini-1.5-flash | ~$0.60 | ~60 minutes |
| gemini-1.5-pro | ~$2.40 | ~90 minutes |

*(Estimates based on average 200 tokens per topic)*

## Troubleshooting

**Model change not taking effect?**
1. Check ConfigManager reloaded: `curl http://localhost:8000/api/settings/robot1_5_llm_model`
2. Verify setting in database
3. If still not working, restart server

**Getting API errors?**
- Ensure the model name is exactly correct (case-sensitive)
- Check your Gemini API key supports the model
- Some experimental models may deprecate over time

## Advanced: Test Different Models

Compare model quality by scoring the same topic with different models:

```bash
# Score with experimental model
curl -X POST http://localhost:8000/api/robots/topic-scorer/run \
  -d '{"batch_size": 5}'

# Change to pro model
curl -X PUT http://localhost:8000/api/settings/robot1_5_llm_model \
  -d '{"value": "gemini-1.5-pro"}'

# Score same topics again (use force_rescore=true)
# Compare scores and profit angles
```

## Related Files

- **Configuration Code**: `src/robots/topic_scorer.py:73-84`
- **LLM Service**: `src/services/llm_service.py:36-62`
- **Settings Script**: `scripts/add_llm_model_config.py`
- **Environment Template**: `.env.example:58`

---

**Generated**: 2025-11-14
**Hot-Reloadable**: ✅ Yes
**Requires Restart**: ❌ No
