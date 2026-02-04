# Integration with CampusConnect

This document describes how the CampusConnect AI service integrates with the main CampusConnect platform and what to verify before connecting.

## Service Architecture

The CampusConnect AI service is a **standalone FastAPI microservice** that runs independently and is called by the main CampusConnect backend.

```
┌─────────────────────────┐
│  CampusConnect Backend  │ (Node.js)
│     (main repo)         │
└────────────┬────────────┘
             │ HTTP POST /run-graph
             │ (graph, input)
             ▼
┌─────────────────────────┐
│  CampusConnect AI       │ (Python)
│  Service (this repo)    │
│                         │
│  ├─ Matching            │
│  ├─ Safety              │
│  ├─ Onboarding          │
│  └─ Events/Communities  │
└────────────┬────────────┘
             │
             ├──────────────────┬────────────────┐
             ▼                  ▼                ▼
       ┌──────────┐        ┌──────────┐  ┌──────────────┐
       │ Firebase │        │Perplexity│  │OpenAI (if no│
       │Firestore │        │   API    │  │Perplexity)  │
       └──────────┘        └──────────┘  └──────────────┘
```

## API Contract

### Request Format
The main backend calls the AI service with:

```bash
POST http://ai-service:8000/run-graph
Content-Type: application/json

{
  "graph": "matching|safety|onboarding|events_communities",
  "input": { /* graph-specific payload */ }
}
```

### Response Format
The service returns:

```json
{
  "success": true,
  "graph": "matching",
  "data": { /* graph-specific output */ },
  "error": null
}
```

On error:
```json
{
  "success": false,
  "graph": "matching",
  "data": {},
  "error": "Error description"
}
```

## Before Connecting to Main Repo

Use this checklist to verify the AI service is ready to integrate with the main CampusConnect backend.

### ✅ Infrastructure & Deployment

- [ ] **Service is running** – Can access health endpoint: `curl http://ai-service:8000/health`
- [ ] **Correct hostname/port** – Main backend knows where to find the service (e.g., `ai-service:8000` for Docker, `localhost:8000` for local dev)
- [ ] **Network connectivity** – Both services can reach each other (firewall rules, VPC setup, etc.)
- [ ] **DNS/discovery** – If using container orchestration, service discovery is configured

### ✅ Firebase Setup

- [ ] **Same Firebase project** – Both services use the same `FIREBASE_PROJECT_ID`
- [ ] **Firestore collections exist** – Collections are created and accessible:
  - `profiles` – User profiles
  - `connections` – User connections/relationships
  - `matches` – Match records created by matching graph
  - `groups` – Student groups/communities
  - `events` – Campus events
  - `helpCategories` – (optional) For help/support chatbot
- [ ] **Service account permissions** – The service account JSON has read/write access to required collections
- [ ] **Multi-tenant filtering** – All Firestore queries in the AI service include `tenantId` and `campusId` filters (verified in code review)

### ✅ Data Schema Alignment

**User Profile Schema** (`profiles/{userId}`):
```javascript
{
  "uid": "user_id",
  "tenantId": "tenant_id",
  "campusId": "campus_id",
  "name": "string",
  "email": "string",
  "major": "string",
  "year": number (1-8),
  "bio": "string",
  "interests": [string],  // Array of interest tags
  "locationLat": number,
  "locationLng": number,
  "createdAt": timestamp
}
```

**Match Record Schema** (`matches/{matchId}`):
```javascript
{
  "user1Id": "uid1",
  "user2Id": "uid2",
  "tenantId": "tenant_id",
  "campusId": "campus_id",
  "baseScore": number (0-100),  // Deterministic score
  "llmScore": number (0-100),   // LLM-adjusted score
  "reasoning": {
    "why_compatible": "string",
    "conversation_starter": "string"
  },
  "createdAt": timestamp,
  "status": "pending|accepted|rejected"
}
```

**Event/Group Schemas** – Verify these exist and have expected fields:
- `events/{eventId}` – `startTime`, `category`, `description`, `attendeesCount`
- `groups/{groupId}` – `name`, `category`, `description`, `memberCount`

### ✅ LLM Configuration

- [ ] **Perplexity key configured** – `PERPLEXITY_API_KEY` is set in `.env` (or secrets manager for production)
- [ ] **Perplexity key valid** – Can call Perplexity API without auth errors
- [ ] **OpenAI fallback set** – `OPENAI_API_KEY` is also configured (in case Perplexity fails)
- [ ] **Model choices made** – Production has chosen appropriate models:
  - Perplexity: `llama-3.1-sonar-small-128k-online` (fast, cheap) or `-large` (better quality)
  - OpenAI: `gpt-3.5-turbo` (cheap) or `gpt-4` (better quality)
- [ ] **Rate limits understood** – Both API providers' rate limits are documented and monitored
- [ ] **Cost monitoring** – Budget alerts set up for LLM API usage

### ✅ Environment Configuration

- [ ] **All required env vars set** – Both production and development `.env` files have:
  - `FIREBASE_PROJECT_ID`
  - `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON)
  - `PERPLEXITY_API_KEY`
  - `OPENAI_API_KEY`
  - `DEBUG` (False in production, True in development)
- [ ] **No secrets in code** – `.env` file is not committed; `.gitignore` includes it
- [ ] **Secrets manager integrated** – Production uses secure secrets storage (AWS Secrets Manager, GCP Secret Manager, etc.)

### ✅ Testing

- [ ] **All unit tests pass** – `pytest tests/unit/ -v`
- [ ] **Smoke tests pass** – `pytest tests/integration/test_smoke.py -v`
- [ ] **Manual E2E test** – Called each graph type from main backend with real data:
  ```bash
  # Test matching
  curl -X POST http://ai-service:8000/run-graph \
    -H "Content-Type: application/json" \
    -d '{
      "graph": "matching",
      "input": {
        "user_id": "real_user_id",
        "tenant_id": "test_tenant",
        "preferences": {"radiusMeters": 5000}
      }
    }'
  
  # Test safety
  curl -X POST http://ai-service:8000/run-graph \
    -H "Content-Type: application/json" \
    -d '{
      "graph": "safety",
      "input": {
        "content": "hello world",
        "content_type": "message",
        "user_id": "test_user",
        "tenant_id": "test_tenant"
      }
    }'
  ```

### ✅ Logging & Monitoring

- [ ] **Logs are structured** – All logs are in JSON format (via `python-json-logger`)
- [ ] **Logs are centralized** – Both services write to same logging backend (Cloud Logging, DataDog, ELK, etc.)
- [ ] **Error tracking integrated** – Error rates and types are visible in monitoring dashboard
- [ ] **Performance monitoring** – Request latencies and timeout rates are tracked
- [ ] **Alerts configured** – Team is notified if:
  - Service is down (health check fails)
  - Error rate exceeds threshold
  - LLM API calls fail repeatedly
  - Response times exceed SLA

### ✅ Security

- [ ] **Firebase rules enforced** – Database rules prevent unauthorized access across tenants/campuses
- [ ] **Input validation** – Main backend validates `user_id` and `tenant_id` before calling AI service
- [ ] **Rate limiting** – If needed, main backend rate-limits calls to AI service per user/tenant
- [ ] **No auth in AI service** – AI service trusts caller to provide valid `user_id` and `tenant_id`
- [ ] **Sensitive data not logged** – User profiles, emails, etc. are not logged except in errors

### ✅ Performance & Reliability

- [ ] **Timeout configured** – `GRAPH_TIMEOUT` is set appropriately (default 30s)
- [ ] **Retry logic tested** – Main backend retries on 5xx errors from AI service
- [ ] **Fallback behavior defined** – If AI service is down, main backend has graceful fallback:
  - Matching: Use deterministic scores only (skip LLM reasoning)
  - Safety: Use pattern matching only (skip LLM classification)
  - Onboarding: Provide text-only prompts (skip LLM guidance)
- [ ] **Load testing done** – Service can handle expected peak load
- [ ] **Docker image optimized** – Production Docker image is small and fast (`docker build -t campusconnect-ai . && docker images`)

## Integration Walkthrough

### Step 1: Verify Service Health
```bash
# From main backend or local dev machine
curl http://ai-service:8000/health

# Expected response:
# {"status":"healthy"}
```

### Step 2: Test Matching Graph
```bash
curl -X POST http://ai-service:8000/run-graph \
  -H "Content-Type: application/json" \
  -d '{
    "graph": "matching",
    "input": {
      "user_id": "alice_uid",
      "tenant_id": "university_1",
      "preferences": {
        "radiusMeters": 5000,
        "minScore": 50
      }
    }
  }'

# Expected response structure:
# {
#   "success": true,
#   "graph": "matching",
#   "data": {
#     "final_matches": [
#       {
#         "match_id": "...",
#         "user_id": "bob_uid",
#         "baseScore": 78,
#         "llmScore": 85,
#         "reasoning": {
#           "why_compatible": "...",
#           "conversation_starter": "..."
#         }
#       }
#     ]
#   }
# }
```

### Step 3: Test Safety Graph
```bash
curl -X POST http://ai-service:8000/run-graph \
  -H "Content-Type: application/json" \
  -d '{
    "graph": "safety",
    "input": {
      "content": "Check out my website: example.com/spam",
      "content_type": "message",
      "user_id": "alice_uid",
      "tenant_id": "university_1"
    }
  }'

# Expected response:
# {
#   "success": true,
#   "graph": "safety",
#   "data": {
#     "safe": false,
#     "flags": ["phishing", "external_link"],
#     "confidence": 0.92,
#     "recommended_action": "review"
#   }
# }
```

### Step 4: Test Onboarding Graph
```bash
curl -X POST http://ai-service:8000/run-graph \
  -H "Content-Type: application/json" \
  -d '{
    "graph": "onboarding",
    "input": {
      "user_id": "charlie_uid",
      "tenant_id": "university_1",
      "current_step": 1,
      "form_data": {
        "name": "Charlie",
        "email": "charlie@university.edu"
      }
    }
  }'

# Expected response:
# {
#   "success": true,
#   "graph": "onboarding",
#   "data": {
#     "current_step": 1,
#     "next_step": 2,
#     "validation_errors": {},
#     "next_prompt": "What is your major?",
#     "guidance": "Tell us about your academic focus"
#   }
# }
```

### Step 5: Test Events/Communities Graph
```bash
curl -X POST http://ai-service:8000/run-graph \
  -H "Content-Type: application/json" \
  -d '{
    "graph": "events_communities",
    "input": {
      "user_id": "david_uid",
      "tenant_id": "university_1",
      "request_type": "events"
    }
  }'

# Expected response:
# {
#   "success": true,
#   "graph": "events_communities",
#   "data": {
#     "recommendations": [
#       {
#         "id": "event_123",
#         "title": "AI Workshop",
#         "category": "tech",
#         "score": 92,
#         "reasoning": "Matches your AI interest"
#       }
#     ]
#   }
# }
```

## Troubleshooting Integration Issues

### Issue: "Connection refused" to AI service
**Solution:** Verify service is running and accessible at correct hostname/port.
```bash
# From main backend container/host
curl http://ai-service:8000/health

# If using localhost in dev:
curl http://localhost:8000/health
```

### Issue: Firestore auth error
**Solution:** Verify service account JSON is in correct location and has correct permissions.
```bash
# Check if file exists
cat /app/config/serviceAccountKey.json | head

# Verify GOOGLE_APPLICATION_CREDENTIALS env var
echo $GOOGLE_APPLICATION_CREDENTIALS
```

### Issue: "No LLM provider configured"
**Solution:** Verify API keys are set in environment.
```bash
# Check if keys are set (don't print actual values!)
test -n "$PERPLEXITY_API_KEY" && echo "Perplexity key is set" || echo "Perplexity key is NOT set"
test -n "$OPENAI_API_KEY" && echo "OpenAI key is set" || echo "OpenAI key is NOT set"
```

### Issue: Matching returns empty matches
**Solution:** Verify Firestore contains test data for the tenant/campus.
```bash
# From main app, query Firestore directly
db.collection("profiles")
  .where("tenantId", "==", "university_1")
  .where("campusId", "==", "campus_1")
  .get()
```

### Issue: Slow response times
**Solution:** Check logs for timeout or LLM API slowness.
```bash
# View recent errors
tail -100 logs/service.log | grep ERROR

# Check if it's LLM provider issue
grep "LLM" logs/service.log | tail -20
```

## Deployment Checklist

Before deploying to production:

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Docker image builds: `docker build -t campusconnect-ai .`
- [ ] Health check works in container: `docker run --rm -p 8000:8000 campusconnect-ai curl http://localhost:8000/health`
- [ ] Env vars are set (not in `.env` file)
- [ ] Firestore schema is finalized and documented
- [ ] LLM provider choice is finalized and budgets are set
- [ ] Logging/monitoring dashboard is set up
- [ ] Alerts are configured
- [ ] Team is trained on service operation and debugging
- [ ] Rollback plan is documented (how to switch back to old version)

## Support & Debugging

For questions or issues:

1. **Check logs** – `tail -100 logs/service.log`
2. **Verify config** – `python -m src.config`
3. **Run tests** – `pytest tests/ -v`
4. **Check API docs** – `curl http://localhost:8000/docs`

