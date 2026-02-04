# CampusConnect AI Service – Overview

## What Is This Service?

CampusConnect AI is a **Python FastAPI microservice** that powers AI-driven features for the CampusConnect platform (a multi-university student networking application).

The service runs **independently** and is called by the main CampusConnect backend via HTTP REST API. It handles four core AI workflows:

1. **Matching** – Find compatible students based on interests, major, location, etc.
2. **Safety** – Moderate user-generated content (detect spam, harassment, misinformation)
3. **Onboarding** – Guide new students through profile setup with intelligent prompts
4. **Events & Communities** – Recommend relevant campus events and student groups

## Architecture

```
┌────────────────────────────────┐
│  Main CampusConnect Backend     │ (Node.js)
│  (main repo)                   │
└──────────────┬─────────────────┘
               │ HTTP POST /run-graph
               │ with (graph, input)
               ▼
┌────────────────────────────────┐
│ CampusConnect AI Service       │ (Python)
│ • FastAPI server               │
│ • LangGraph agents             │
│ • Deterministic + LLM scoring  │
└──────────────┬─────────────────┘
               │
       ┌───────┴────────┬──────────────┐
       ▼                ▼              ▼
   ┌───────┐      ┌──────────┐   ┌──────────┐
   │Firebase│      │Perplexity│   │OpenAI    │
   │Firestore      │(primary) │   │(fallback)│
   │(data)         │(LLM)     │   │(LLM)     │
   └───────┘       └──────────┘   └──────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Server** | FastAPI + uvicorn |
| **AI Agents** | LangChain + LangGraph |
| **Database** | Firebase Firestore (read/write) |
| **LLM** | Perplexity Sonar (primary) + OpenAI (fallback) |
| **Language** | Python 3.12 |
| **Testing** | pytest + pytest-asyncio |
| **Containerization** | Docker (multi-stage) |

## How It Works

### Matching Flow

```
User A requests matches
    ↓
1. Fetch user profile from Firestore
2. Query all candidates in same campus/tenant
3. Filter candidates by distance/basic compatibility
4. Score candidates deterministically (0-100 scale)
5. Call LLM to generate reasoning for top candidates
   ("Why are they compatible?", "Conversation starter")
6. Return top matches with scores + LLM reasoning
```

### Safety Flow

```
User posts message
    ↓
1. Fast pattern matching for obvious spam/phishing
2. If uncertain, call LLM to classify content
3. Return flags (spam, harassment, etc.) + recommendation
   (allow, review, reject)
```

### Onboarding Flow

```
New user joins
    ↓
1. Present profile form (name, email, major, interests, etc.)
2. When user submits form data, validate it
3. Call LLM to generate next prompt based on progress
4. Repeat until profile complete
5. Save completed profile to Firestore
```

### Events/Communities Flow

```
User requests recommendations
    ↓
1. Fetch user profile from Firestore
2. Query all events/groups in user's campus
3. Score them deterministically (event time, category match, etc.)
4. Call LLM to explain why each item is recommended
5. Return ranked recommendations
```

## Key Features

✅ **Multi-Tenant** – All data queries filter by `tenantId` and `campusId`  
✅ **Deterministic + LLM** – Fast scoring first, then LLM reasoning (cost-efficient)  
✅ **Provider Fallback** – Perplexity is primary, OpenAI is fallback  
✅ **Structured Logging** – JSON logs for easy parsing and monitoring  
✅ **Comprehensive Testing** – Unit, integration, and smoke tests  
✅ **Docker Ready** – Multi-stage build for optimized production image  

## Quick Start

### Local Development

```bash
# 1. Clone repo
git clone <repo-url>
cd campusconnect-ai

# 2. Create .env from template
cp .env.example .env
# Edit .env and add your credentials:
# - FIREBASE_PROJECT_ID
# - GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON)
# - PERPLEXITY_API_KEY
# - OPENAI_API_KEY (optional, fallback)

# 3. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run server
python -m uvicorn src.server:app --reload

# 6. Test the service
curl http://localhost:8000/health
# {"status":"healthy"}

# 7. View API docs
# Open http://localhost:8000/docs in browser
```

### Docker

```bash
# Build image
docker build -t campusconnect-ai .

# Run container
docker run --rm \
  -e FIREBASE_PROJECT_ID=my-project \
  -e PERPLEXITY_API_KEY=pplx-xxxxx \
  -v /path/to/serviceAccountKey.json:/config/serviceAccountKey.json \
  -p 8000:8000 \
  campusconnect-ai

# Test
curl http://localhost:8000/health
```

## API Endpoints

### Health Check
```bash
GET /health
# {"status":"healthy"}
```

### Run Graph
```bash
POST /run-graph
Content-Type: application/json

{
  "graph": "matching|safety|onboarding|events_communities",
  "input": { /* graph-specific payload */ }
}
```

See [docs/INTEGRATION_CAMPUSCONNECT.md](./INTEGRATION_CAMPUSCONNECT.md) for detailed request/response examples.

## Project Structure

```
campusconnect-ai/
├── src/
│   ├── server.py                 # FastAPI app (main entrypoint)
│   ├── config.py                 # Configuration from env vars
│   ├── state.py                  # LangGraph state definitions
│   ├── graphs/                   # AI agent implementations
│   │   ├── matching.py
│   │   ├── safety.py
│   │   ├── onboarding.py
│   │   ├── events_communities.py
│   │   └── base_graph.py        # Base class for graphs
│   ├── tools/                    # Reusable functions
│   │   ├── llm_client.py        # LLM provider selection (Perplexity + OpenAI)
│   │   ├── llm_tools.py         # LLM chains for each graph
│   │   ├── firestore_tools.py   # Firestore queries
│   │   └── scoring_tools.py     # Deterministic scoring
│   └── utils/
│       ├── errors.py            # Custom exceptions
│       ├── geo.py               # Haversine distance
│       └── logging_config.py    # Logging setup
├── tests/
│   ├── unit/                    # Unit tests
│   │   ├── tools/
│   │   ├── graphs/
│   │   └── test_config.py
│   ├── integration/             # Integration tests
│   │   └── test_smoke.py
│   └── conftest.py              # Pytest fixtures
├── docs/                        # Documentation
│   ├── TESTING.md              # How to run tests
│   ├── INTEGRATION_CAMPUSCONNECT.md  # Integration checklist
│   └── ... (other docs)
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── Dockerfile                   # Production Docker image
└── README.md                    # This file
```

## Testing

Run tests with:

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=src
```

See [docs/TESTING.md](./docs/TESTING.md) for detailed testing guide.

## Configuration

All configuration comes from environment variables (`.env` file or production secrets).

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FIREBASE_PROJECT_ID` | ✅ | – | Firebase project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | ✅ | `/config/serviceAccountKey.json` | Path to service account JSON |
| `PERPLEXITY_API_KEY` | (one LLM) | – | Perplexity API key (primary provider) |
| `OPENAI_API_KEY` | (one LLM) | – | OpenAI API key (fallback provider) |
| `DEBUG` | ✓ | False | Enable debug logging |
| `GRAPH_TIMEOUT` | ✓ | 30 | Max seconds for graph execution |
| `PORT` | ✓ | 8000 | Server port |

See `.env.example` for full list with descriptions.

## LLM Provider Strategy

The service uses a **Perplexity-first, OpenAI-fallback** strategy:

1. **Perplexity** (primary)
   - Cheaper than OpenAI
   - Built-in web search capability
   - Model: `llama-3.1-sonar-small-128k-online` (fast)
   - Requires: `PERPLEXITY_API_KEY`

2. **OpenAI** (fallback)
   - Used if Perplexity key is not set
   - Model: `gpt-3.5-turbo` (default) or `gpt-4` (better quality)
   - Requires: `OPENAI_API_KEY`

If neither key is set, the service will fail at startup with a clear error message.

## Integration with CampusConnect

See [docs/INTEGRATION_CAMPUSCONNECT.md](./docs/INTEGRATION_CAMPUSCONNECT.md) for:

- **Integration checklist** – What to verify before connecting to main backend
- **API contract** – Request/response formats for each graph
- **Firestore schema** – Expected data structure
- **Troubleshooting** – Common issues and fixes
- **Deployment guide** – Production readiness checklist

## Contributing

When adding features:

1. Write tests first (TDD)
2. Follow the existing code style (imports, docstrings, etc.)
3. Update relevant docs
4. Ensure `pytest tests/ -v` passes
5. Update CHANGELOG if adding significant features

## Support

For questions or issues, check:

1. [docs/TESTING.md](./docs/TESTING.md) – How to run tests and debug
2. [docs/INTEGRATION_CAMPUSCONNECT.md](./docs/INTEGRATION_CAMPUSCONNECT.md) – Integration issues
3. `logs/service.log` – Application logs
4. `curl http://localhost:8000/docs` – Interactive API documentation

## License

[Add license info here]

## See Also

- [Testing Guide](./docs/TESTING.md) – How to run and write tests
- [Integration Guide](./docs/INTEGRATION_CAMPUSCONNECT.md) – Connecting to main backend
- [Main CampusConnect Repo](../campusconnect) – Main application

