# Setup Guide

Complete step-by-step instructions to get CampusConnect AI running locally.

## Prerequisites

- **Python 3.9+** (check: `python --version`)
- **pip** (comes with Python)
- **git** (check: `git --version`)
- **Firebase project** (free tier ok)
- **LLM API key** (Perplexity or OpenAI)

## Step 1: Clone the repository

```bash
git clone https://github.com/yourusername/campusconnect-ai.git
cd campusconnect-ai
```

## Step 2: Create a Python virtual environment

```bash
# Create venv
python -m venv venv

# Activate venv
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

## Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

This installs:

- fastapi, uvicorn – API framework
- langgraph, langchain – AI orchestration
- firebase-admin – Firebase integration
- python-dotenv – Environment variable management
- pydantic – Data validation

## Step 4: Set up environment variables

Copy the template:

```bash
cp .env.example .env
```

Edit .env and fill in your values:

```text
# Firebase (REQUIRED)
FIREBASE_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./config/serviceAccountKey.json

# LLM (REQUIRED – choose ONE)
PERPLEXITY_API_KEY=pplx-your-key-here
# OR
OPENAI_API_KEY=sk-proj-your-key-here

# Optional
AI_SERVICE_TOKEN=your-shared-secret-here
DEBUG=true
```

### Getting Firebase credentials

1. Go to Firebase Console
2. Create or select a project
3. Go to Settings (⚙️ icon) → Service Accounts
4. Click Generate new private key
5. Save the JSON file as config/serviceAccountKey.json in this repo
6. Get your Project ID from Settings → General tab

### Getting an LLM API key

**Perplexity (recommended – cheaper):**
1. Go to https://www.perplexity.ai/settings/api
2. Click Create API Key
3. Copy the key (starts with pplx-)
4. Add to .env: PERPLEXITY_API_KEY=pplx-...

**OpenAI (fallback):**
1. Go to https://platform.openai.com/api-keys
2. Click Create new secret key
3. Copy the key (starts with sk-proj-)
4. Add to .env: OPENAI_API_KEY=sk-proj-...

## Step 5: Run the service

```bash
uvicorn src.server:app --reload
```

Output:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

## Step 6: Test the API

1. Open http://localhost:8000/docs in your browser
2. You should see the Swagger UI with all endpoints
3. Click Try it out on /run-graph and test with sample payloads (see README.md)

## Troubleshooting

**ModuleNotFoundError: No module named 'fastapi'**  
You didn't install dependencies. Run:

```bash
pip install -r requirements.txt
```

**firebase_admin.exceptions.InvalidArgumentError: Certificate not found at path...**  
Firebase credentials missing. Download from Firebase Console and save to:

```text
config/serviceAccountKey.json
```

**Unauthorized: Invalid API key for Perplexity**  
Check your PERPLEXITY_API_KEY in .env is correct and not empty.

**Graph times out after 30 seconds**  
Some LLM calls are slow. Increase GRAPH_TIMEOUT in .env:

```text
GRAPH_TIMEOUT=60
```

**Port 8000 already in use**  
Run on a different port:

```bash
uvicorn src.server:app --reload --port 8001
```

## Next steps

- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) to understand the system design
- Read [docs/API.md](docs/API.md) for endpoint details
- Check [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production setup
