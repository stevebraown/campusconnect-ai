# CampusConnect AI Agent Setup – Information Gathering (Filled From Repo)

This document answers the **CampusConnect AI Agent Setup - Information Gathering Prompt** using the current **campusconnect-ai** repository. Use it as a single source of truth for project state and for handoff.

---

## Section 1: Project Foundation & Existing Setup

### 1. Current Project Structure
- **Python project location:** `campusconnect-ai/` (sibling to main app repo `campusconnect/`).
- **requirements.txt:** Yes. Present at repo root with pinned versions (FastAPI, uvicorn, langchain, langgraph, firebase-admin, etc.).
- **pyproject.toml:** No. Dependency management is via `requirements.txt` only.
- **.env template:** Yes. `.env.example` exists with commented sections for Firebase, Perplexity, OpenAI, LangSmith, graph settings, and server config. Copy to `.env` and fill values.
- **Main entry point:** `src/server.py` – FastAPI app. Run with: `python -m uvicorn src.server:app --reload`.

### 2. AI Agent Framework
- **Framework:** LangChain + LangGraph. Graphs are built with `StateGraph`; nodes are pure functions; tools live in `src/tools/` (Firestore, LLM chains, scoring).
- **Existing code:** Yes. Full structure: `src/graphs/` (matching, safety, onboarding, events_communities, base_graph), `src/tools/` (firestore_tools, llm_tools, scoring_tools), `src/utils/`, `src/config.py`, `src/state.py`.
- **LLM provider:** Perplexity Sonar (primary) via OpenAI-compatible API (`base_url=https://api.perplexity.ai`). OpenAI as optional fallback if `PERPLEXITY_API_KEY` is not set.

### 3. Current Frontend/Backend Stack (Assumed From Prompt)
- **Frontend API calls:** Not in this repo; main app is JS (React). This service is the backend for AI.
- **Backend being used:** This Python service (FastAPI). Node/Firebase backend is expected to call it at `POST http://ai-service:8000/run-graph` with `{ graph, input }`.
- **Mock AI endpoint:** N/A here. Frontend would call the main backend, which then calls this service’s `/run-graph`.

---

## Section 2: API Keys & Credentials

### 4. LLM API Keys
- **Primary LLM:** Perplexity Sonar. **Fallback:** OpenAI (optional).
- **Keys:** Set in `.env`: `PERPLEXITY_API_KEY` (primary), optionally `OPENAI_API_KEY` and `OPENAI_MODEL`.
- **Preferred model:** Perplexity: `llama-3.1-sonar-small-128k-online` (configurable via `PERPLEXITY_MODEL`). OpenAI fallback: `gpt-3.5-turbo` (or set `OPENAI_MODEL`).
- **Pricing/limits:** Perplexity is documented as cheaper; rate limits depend on provider. No special budget logic in code.

### 5. Firebase Setup
- **Firebase usage:** Yes. Firestore via Firebase Admin SDK for profiles, connections, matches, events, groups. Same `serviceAccountKey.json` as main app.
- **Firebase project:** Required. `FIREBASE_PROJECT_ID` in `.env`.
- **Admin credentials:** Required. `GOOGLE_APPLICATION_CREDENTIALS` must point to `config/serviceAccountKey.json` (local: `./config/serviceAccountKey.json`; Docker: mount and set path, e.g. `/app/config/serviceAccountKey.json`).
- **Hosting:** Python agent runs as its own service (local or Docker). Not inside Firebase Functions.

### 6. Other API Integrations
- **Geolocation:** No external geolocation API. Haversine in `src/utils/geo.py` for distance; coordinates come from Firestore profiles.
- **University APIs:** None in this repo. Data is from Firestore (profiles, events, groups).
- **Other APIs:** None. Only Firebase, Perplexity (or OpenAI), and optional LangSmith.

---

## Section 3: AI Agent Design & Purpose

### 7. Agent Responsibilities
- **Main tasks:** (1) Student matching (deterministic + LLM reasoning), (2) content safety/moderation (pattern + LLM), (3) onboarding flow (validation + LLM guidance), (4) events/communities recommendations.
- **Features powered:** Matching suggestions with “why compatible” and conversation starters; content flags (spam, explicit, phishing) and allow/review/reject; onboarding steps and next prompts; ranked events/groups with reasoning.
- **Data access:** Firestore: profiles, connections, matches, events, groups. All filtered by `campusId` and `tenantId` (multi-tenant).
- **Actions:** Read profiles/connections/events/groups; write matches (and onboarding progress in onboarding graph). No direct “send notification” in this service; that would be in the main backend.

### 8. Agent Tools & Functions
- **Tools:** Implemented in `src/tools/`:  
  - **firestore_tools:** `get_user_profile`, `get_all_profiles_in_campus`, `get_user_connections`, `get_recent_matches`, `save_match`, `get_all_events`, `get_all_groups`, `validate_user_exists`.  
  - **llm_tools:** `get_llm()`, matching reasoning chain, safety classification chain, onboarding guidance chain, recommendations ranking chain.  
  - **scoring_tools:** `calculate_base_compatibility_score`, `calculate_distance_score`, `filter_candidates_basic`.
- **Backend vs external:** Firestore = backend DB; LLM = Perplexity/OpenAI. No separate “backend API” calls from this repo; this service is the AI backend.

### 9. Conversation & Context
- **Memory:** No long-lived conversation memory in this service. Each `/run-graph` call is stateless; input carries `user_id`, `tenant_id`, and graph-specific payload (e.g. `form_data`, `content`).
- **Storage:** State is in the request/response and Firestore (e.g. onboarding progress saved to profiles). No dedicated “conversation history” store in this repo.
- **History limit:** N/A for this service; if the main app wants history, it would store it and pass relevant context in `input`.

---

## Section 4: Frontend Integration Details

### 10. Frontend Architecture
- **Stack:** Not in this repo. Main app is JS (React) in a separate repo; this repo is Python-only.
- **API surface for frontend:** Frontend talks to the main backend; backend calls this service at `POST /run-graph` with `{ "graph": "matching"|"safety"|"onboarding"|"events"|"communities", "input": { ... } }`. See README and `src/server.py` for request/response shapes.

### 11. Authentication & Authorization
- **Auth:** Not implemented in this service. Caller (main backend) is expected to authenticate users and pass `user_id` and `tenant_id` in `input`. This service does not verify tokens; it trusts the caller.
- **Permissions:** Same `user_id`/`tenant_id` are used for Firestore multi-tenant filtering. Different “user types” would be enforced by the main backend before calling this service.

### 12. Real-time Updates
- **Real-time:** No WebSockets or Firebase listeners in this service. Interaction is request/response over HTTP.
- **Delivery:** REST only. Response from `/run-graph` is JSON (success, graph name, data, error).
- **Streaming:** No token-by-token streaming; full graph result is returned when the graph completes.

---

## Section 5: Backend Infrastructure

### 13. Backend Hosting & Deployment
- **Where it runs:** Standalone Python service (local or container). Dockerfile present; build: `docker build -t campusconnect-ai .`, run with env and optional mount for `serviceAccountKey.json`.
- **Deployed vs local:** Can be local-only or deployed (e.g. same host/network as Node backend, or separate service). No deployment platform specified in repo.
- **Strategy:** Python 3.12, uvicorn, optional Docker multi-stage build. No serverless (e.g. Firebase Functions) in this repo.

### 14. Database & Storage
- **CampusConnect data:** Firestore (profiles, connections, matches, groups, events, helpCategories as per original spec). This service reads/writes via Firebase Admin.
- **Agent conversation history:** Not stored by this service. Onboarding progress is written to Firestore profiles.
- **Data models:** No formal schema file in repo. Shapes implied by `src/state.py` (TypedDicts) and Firestore tool usage (e.g. `campusId`, `tenantId`, `uid`, `locationLat/Lng`, `interests`, etc.).

### 15. API Communication
- **Existing backend APIs:** This service does not call other HTTP APIs except Perplexity/OpenAI and Firebase. The main backend calls this service.
- **HTTP API:** Yes. FastAPI: `GET /health`, `POST /run-graph`, plus `GET /docs`, `GET /openapi.json`.
- **CORS:** Middleware allows origins (configurable); typically backend and frontend on different domains.
- **Rate limiting:** Not implemented in the provided code.

---

## Section 6: Environment & Dependencies

### 16. Python Environment
- **Version:** 3.12+ (documented in README; Dockerfile uses `python:3.12-slim`).
- **Virtual environment:** Recommended (e.g. `python3 -m venv .venv`). Not committed; `.venv/` in `.gitignore`.
- **Location:** Repo root; activate before running (e.g. `source .venv/bin/activate`).

### 17. Required Dependencies
- **List:** See `requirements.txt`: fastapi, uvicorn, pydantic, pydantic-settings, python-dotenv, langchain, langgraph, langchain-openai, openai, firebase-admin, python-json-logger, langsmith, requests, httpx (with versions).
- **Versions:** Pinned in `requirements.txt` for reproducibility.
- **Async:** FastAPI/uvicorn are async-capable; graph execution may run in thread pool (see server code). No aiohttp in requirements.

### 18. Development Environment
- **Replit vs local:** Setup is standard (venv + .env). No Replit-specific config. Works on macOS/Linux; Windows should work with path adjustments for `GOOGLE_APPLICATION_CREDENTIALS`.

---

## Section 7: Specific Features & Requirements

### 19. Agent Behavior & Constraints
- **Instructions:** Encoded in prompts in `src/tools/llm_tools.py` (matching advisor, content moderator, onboarding assistant, recommendations). No single “system prompt” file; each chain has its own template.
- **Refusals:** Safety graph flags content and recommends allow/review/reject; no explicit “refuse request” logic beyond that.
- **Tone:** Professional/friendly (e.g. “student relationship advisor”, “content moderator for a university social platform”).
- **Response length:** Prompt text asks for 100–150 words for “why compatible”; others are open-ended. No hard length limits in code.

### 20. Data Privacy & Safety
- **Never access:** This service does not receive passwords; it receives `user_id`, `tenant_id`, and graph inputs. Secrets (API keys, service account) are in env/files only.
- **User confirmation:** Not implemented here; main app can require confirmation before calling certain graphs.
- **Regulatory:** No GDPR-specific logic; multi-tenant isolation and minimal data in logs are the main considerations.
- **Audit logging:** Application logging exists; no dedicated “audit log” of every agent action. Could be added via middleware or Firestore writes.

### 21. Error Handling & Fallbacks
- **API failures:** Firestore errors raise `FirestoreUnavailableError`; graph nodes set `error` in state and return graceful fallbacks (e.g. empty matches). LLM failures in chains can fall back to deterministic scores or default messages.
- **LLM unavailable:** If neither Perplexity nor OpenAI is configured, `get_llm()` raises. If one fails at runtime, the other is not auto-tried in the same request; fallbacks are per-graph (e.g. skip reasoning, use deterministic only).
- **Manual override:** Not in this service; would be in main backend or admin tooling.
- **Errors to frontend:** Returned as `success: false` and `error: "<message>"` in JSON response; HTTP 4xx/5xx for invalid graph name or server errors as appropriate.

---

## Section 8: Timeline & Current Blockers

### 22. Current State Assessment
- **Working:** Project structure, config loading, four LangGraph graphs (matching, safety, onboarding, events_communities), Firestore tools, LLM chains (Perplexity/OpenAI), scoring, FastAPI server, `/health` and `/run-graph`, Dockerfile, `.env.example`, README, config path fixed to `./config/serviceAccountKey.json` for local.
- **Needs filling in:** `.env` values (Firebase project, credentials path, Perplexity or OpenAI key), actual `config/serviceAccountKey.json` file. Optional: LangSmith keys for tracing.
- **Priority:** Repo is “implemented”; next step is fill env, run locally, then integrate with main backend and frontend.

### 23. Integration Points
- **(a) .env:** Documented in `.env.example` and `config/README.md`. Required: `FIREBASE_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`, and either `PERPLEXITY_API_KEY` or `OPENAI_API_KEY`.
- **(b) APIs:** Firebase and LLM only; no extra API setup beyond keys and service account path.
- **(c) Agent logic/tools:** Implemented; extend by adding nodes or tools if needed.
- **(d) Frontend–backend:** Main backend must `POST` to this service’s `/run-graph`; frontend continues to call main backend.
- **(e) Deployment:** Dockerfile present; deployment steps depend on target (e.g. Cloud Run, ECS, same host as Node).

---

## Your Complete Checklist (From Prompt)

| Deliverable | Status |
|------------|--------|
| Step-by-step setup guide | README.md + this doc |
| Sample `.env` | `.env.example` (copy to `.env` and fill) |
| Python project structure | Present under `src/` |
| Agent with tools | Graphs + tools in `src/graphs/`, `src/tools/` |
| API endpoints for frontend | `GET /health`, `POST /run-graph` |
| Frontend integration code | In main app repo; call backend that calls this service |
| Deployment instructions | README + Dockerfile; platform-specific steps as needed |
| Testing & debugging | README; optional LangSmith |
| Common issues & solutions | README / docs; e.g. credential path, missing keys |

---

## Quick Start (Reminder)

1. **Python 3.12+:** `python3 --version`
2. **Venv:** `python3 -m venv .venv` then `source .venv/bin/activate`
3. **Deps:** `pip install -r requirements.txt`
4. **Env:** `cp .env.example .env`; set `FIREBASE_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS=./config/serviceAccountKey.json`, and `PERPLEXITY_API_KEY` (or `OPENAI_API_KEY`).
5. **Firebase key:** Save service account JSON as `config/serviceAccountKey.json`.
6. **Run:** From repo root: `python -m uvicorn src.server:app --reload`
7. **Test:** `curl http://localhost:8000/health` then `curl -X POST http://localhost:8000/run-graph -H "Content-Type: application/json" -d '{"graph":"matching","input":{"user_id":"...","tenant_id":"...","preferences":{}}}'`

---

*Generated from the campusconnect-ai repository. Update this file when the project or the main app integration changes.*
