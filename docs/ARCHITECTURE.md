# Architecture

Technical design of the CampusConnect AI Service.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Server (http://localhost:8000)                      │
├─────────────────────────────────────────────────────────────┤
│ POST /run-graph                                              │
│  ├─ Validates request (graph name, input state)              │
│  ├─ Routes to correct LangGraph                              │
│  └─ Returns { success, graph, data, error }                  │
│                                                             │
│   ┌───────────────────────────────────────────────────────┐ │
│   │ LangGraph Agents (src/graphs/)                         │ │
│   ├───────────────────────────────────────────────────────┤ │
│   │ 1) Matching                                             │ │
│   │ 2) Safety                                               │ │
│   │ 3) Onboarding                                           │ │
│   │ 4) Events/Communities                                   │ │
│   └───────────────────────────────────────────────────────┘ │
│                                                             │
│   ┌───────────────────────────────────────────────────────┐ │
│   │ External Services                                      │ │
│   ├───────────────────────────────────────────────────────┤ │
│   │ Firebase/Firestore  ← User profiles & data             │ │
│   │ Perplexity/OpenAI  ← LLM reasoning                      │ │
│   │ LangSmith (opt.)  ← LLM tracing/debug                  │ │
│   └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Graph Details

### 1) Matching Graph (`src/graphs/matching.py`)

**Purpose:** Find compatible students to connect with.

**Input state:**
```json
{
  "user_id": "uid-123",
  "tenant_id": "university-1",
  "preferences": {
    "radiusMeters": 200000,
    "minScore": 30
  }
}
```

**Process:**
1. Fetch candidates from Firestore (filter by tenant + geography).
2. Deterministic scoring (distance, interests, signals).
3. LLM reasoning to refine ranking + provide explanations.
4. Return final matches.

**Output:**
```json
{
  "final_matches": [
    { "user_id": "u2", "score": 78, "reason": "Shared interests + proximity" }
  ],
  "response_metadata": { "count": 1, "provider": "perplexity" }
}
```

### 2) Safety Graph (`src/graphs/safety.py`)

**Purpose:** Moderate content for safety policy compliance.

**Input state:**
```json
{
  "user_id": "uid-123",
  "tenant_id": "university-1",
  "content": "Hello!",
  "content_type": "message"
}
```

**Process:**
1. Pattern matching for obvious violations.
2. LLM classification for nuanced cases.
3. Generate safe/unsafe label + confidence.

**Output:**
```json
{
  "safe": true,
  "confidence": 0.92,
  "recommended_action": "allow"
}
```

### 3) Onboarding Graph (`src/graphs/onboarding.py`)

**Purpose:** Guide profile collection with validation and suggestions.

**Input state:**
```json
{
  "user_id": "uid-123",
  "tenant_id": "university-1",
  "form_data": {
    "major": "Computer Science",
    "interests": ["AI", "Robotics"]
  }
}
```

**Process:**
1. Validate required fields.
2. LLM provides suggestions or next-step prompts.
3. Return next step and any validation errors.

**Output:**
```json
{
  "currentStep": 2,
  "validationErrors": [],
  "nextPrompt": "Tell us about your clubs or activities."
}
```

### 4) Events/Communities Graph (`src/graphs/events_communities.py`)

**Purpose:** Recommend events and groups based on interests and location.

**Input state:**
```json
{
  "user_id": "uid-123",
  "tenant_id": "university-1",
  "interests": ["AI", "Startups"],
  "location": { "lat": 37.77, "lng": -122.42 }
}
```

**Process:**
1. Filter candidate events/groups.
2. LLM ranks results.
3. Return ranked events and groups.

**Output:**
```json
{
  "events": [{ "id": "evt-1", "score": 0.88 }],
  "groups": [{ "id": "grp-2", "score": 0.82 }]
}
```

## Request/Response Shape

All graphs return a consistent envelope:

```json
{
  "success": true,
  "graph": "matching",
  "data": { "..." : "..." },
  "error": null
}
```

Errors:

```json
{
  "success": false,
  "graph": "matching",
  "data": null,
  "error": "Human-readable error message"
}
```

## Error Handling

- 400 — invalid input or graph name
- 401 — missing/invalid API token (if enabled)
- 500 — internal server error
- 504 — graph timeout

## Performance Notes

- Typical latency: 2–5 seconds per graph call (LLM dependent)
- Timeout: 30 seconds default (configurable via GRAPH_TIMEOUT)
- Candidate limit: 100 default (configurable via MAX_CANDIDATES)
