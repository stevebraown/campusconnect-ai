# CampusConnect AI Service

FastAPI + LangGraph AI agents for multi-university matching, safety, onboarding, and event/community recommendations.

## Agents

The service exposes five LangGraph agents:

| Agent | Purpose |
|-------|---------|
| **matching** | Student compatibility scoring (deterministic + LLM reasoning). |
| **onboarding** | Guided profile collection with AI validation. |
| **events** | Event and community recommendations based on interests. |
| **safety** | Content moderation (pattern + LLM hybrid). |
| **help** | User support queries and FAQ responses (Perplexity + optional Firestore FAQs). |

## Features

- **Matching** – Student compatibility scoring (deterministic + LLM reasoning).
- **Safety** – Content moderation (pattern + LLM hybrid).
- **Onboarding** – Guided profile collection with AI validation.
- **Events & Communities** – Event/group recommendations based on interests.
- **Help** – Support and FAQ answers (concise, under 500 chars; optional Firestore help articles).

## Tech Stack

- **FastAPI** – High-performance async API framework.
- **LangGraph** – Orchestration framework for AI agents.
- **Firebase / Firestore** – User data and matches.
- **Perplexity / OpenAI** – LLM reasoning (Perplexity recommended for cost).
- **LangChain** – LLM integration & utilities.

## Quick Start

### Prerequisites
- Python 3.9+
- Firebase project with Firestore
- Perplexity or OpenAI API key

### Installation

1. **Clone the repo**
   ```bash
   git clone https://github.com/yourusername/campusconnect-ai.git
   cd campusconnect-ai
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Firebase project ID, LLM API key, etc.
   ```

3. **Install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

4. **Add Firebase credentials**
   ```bash
   # Download service account key from Firebase Console
   # Save to: config/serviceAccountKey.json
   ```

5. **Run the service**
   ```bash
   uvicorn src.server:app --reload
   ```
   API: http://localhost:8000  
   Swagger UI: http://localhost:8000/docs

## API Overview

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /health | GET | Health check |
| /run-graph | POST | Execute any graph by name (matching, safety, onboarding, events_communities, help) |
| /api/ai-match | POST | Matching agent (spec-compliant) |
| /api/ai-onboarding | POST | Onboarding agent (spec-compliant) |
| /api/ai-events | POST | Events/communities agent (spec-compliant) |
| /api/ai-safety | POST | Safety/moderation agent (spec-compliant) |
| /api/ai-help | POST | Help/FAQ agent (spec-compliant) |
| /docs | GET | Interactive Swagger UI |
| /openapi.json | GET | OpenAPI schema |

See [docs/API.md](docs/API.md) for detailed endpoint documentation.

### API Endpoints (examples)

**Matching** – `POST /api/ai-match`
```json
{
  "user_id": "user-123",
  "tenant_id": "university-1",
  "preferences": { "radiusMeters": 200000, "minScore": 30 }
}
```

**Onboarding** – `POST /api/ai-onboarding`
```json
{
  "user_id": "user-123",
  "tenant_id": "university-1",
  "form_data": { "name": "Jane", "email": "jane@example.com" }
}
```

**Events** – `POST /api/ai-events`
```json
{
  "user_id": "user-123",
  "tenant_id": "university-1",
  "request_type": "events",
  "filters": {}
}
```

**Safety** – `POST /api/ai-safety`
```json
{
  "user_id": "user-123",
  "content": "Hello, let's be friends!",
  "content_type": "message",
  "tenant_id": "university-1"
}
```

**Help** – `POST /api/ai-help`
```json
{
  "query": "How do I change my profile?",
  "user_id": "user-123",
  "tenant_id": "university-1"
}
```
Response includes `response`, `sources` (FAQ IDs), and `confidence`.

## Project Structure

```
campusconnect-ai/
├── src/
│   ├── graphs/
│   │   ├── matching.py           # Matching graph
│   │   ├── safety.py             # Safety/moderation graph
│   │   ├── onboarding.py         # Onboarding graph
│   │   ├── events_communities.py # Events/groups graph
│   │   └── help.py               # Help/FAQ graph
│   ├── tools/
│   │   ├── firestore_tools.py    # Firebase access
│   │   ├── llm_client.py         # LLM provider selection
│   │   ├── llm_tools.py          # LLM chains/prompts
│   │   └── scoring_tools.py      # Deterministic scoring
│   ├── utils/
│   │   ├── logging_config.py
│   │   ├── errors.py
│   │   └── geo.py
│   ├── config.py                 # Configuration & env vars
│   └── server.py                 # FastAPI app
├── config/
│   └── serviceAccountKey.json    # Firebase credentials (NOT in git)
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── SETUP.md                      # Detailed setup guide
├── docs/
│   ├── ARCHITECTURE.md           # System design & graphs
│   ├── API.md                    # Endpoint reference
│   ├── DEPLOYMENT.md             # Production deployment
│   └── CONTRIBUTING.md           # Contribution guidelines
└── LICENSE                       # License (MIT)
```

## Documentation

- [SETUP.md](SETUP.md) – Step-by-step installation & configuration
- [ARCHITECTURE](docs/ARCHITECTURE.md) – System design, graph descriptions, data flows
- [API Reference](docs/API.md) – Complete endpoint reference with examples
- [Deployment & Operations](docs/DEPLOYMENT.md) – Production deployment & operations
- [Contributing](docs/CONTRIBUTING.md) – How to contribute

## Testing

Manual testing via Swagger UI:

1. Open http://localhost:8000/docs  
2. Expand `/run-graph` and try sample payloads:

**Matching**
```json
{
  "graph": "matching",
  "input": {
    "user_id": "test-user-123",
    "tenant_id": "university-1",
    "preferences": { "radiusMeters": 200000, "minScore": 30 }
  }
}
```

**Safety**
```json
{
  "graph": "safety",
  "input": {
    "user_id": "test-user-123",
    "content": "Hello, let's be friends!",
    "content_type": "message"
  }
}
```

## Environment Variables

**Required**
- **FIREBASE_PROJECT_ID** – Firebase project ID (Firestore).
- **GOOGLE_APPLICATION_CREDENTIALS** – Path to Firebase service account JSON (e.g. `./config/serviceAccountKey.json`).
- **PERPLEXITY_API_KEY** (or **OPENAI_API_KEY**) – LLM for reasoning and help answers (Perplexity recommended for cost).

**Optional**
- **AI_SERVICE_TOKEN** – Shared secret for `/run-graph` and `/api/ai-*` auth (Bearer token).
- **LANGSMITH_API_KEY** – LLM tracing.
- **DEBUG** – Verbose logs.
- **GRAPH_TIMEOUT** – Graph execution timeout in seconds (default 30).

**Firestore:** Use Firebase Console → Project Settings → Service Accounts → Generate new private key; save as `config/serviceAccountKey.json`. See [SETUP.md](SETUP.md).

**Perplexity:** Get an API key from [Perplexity API settings](https://www.perplexity.ai/settings/api); set `PERPLEXITY_API_KEY=pplx-...` in `.env`.

See `.env.example` for the full list with explanations.

## Performance & Limits

- Graph timeout: 30 seconds (configurable)
- Max candidates: 100 per query (configurable)
- Typical latency: 2–5 seconds per /run-graph call (LLM-dependent)

## License

MIT License — see LICENSE.

## Support

Open an issue on GitHub for bugs, questions, or feature requests.
