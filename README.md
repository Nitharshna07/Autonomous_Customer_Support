# Autonomous Customer Support Copilot

An enterprise-ready, full-stack **Autonomous Customer Support Copilot** web application built with FastAPI, SQLite/SQLAlchemy, Scikit-learn TF-IDF RAG, pluggable LLM provider engine, intent routing, auto-escalation ticket management, and a React + Vite support command console.

---

## Key Features

- **Pluggable LLM Layer**: Zero-code switching between `template` (zero-setup rule fallback), `ollama` (local LLM), `anthropic` (Claude 3.5), and `openai` (GPT-4o-mini).
- **Zero-GPU RAG Engine**: Instant document grounding using TF-IDF + Cosine Similarity over `.txt`, `.md`, and `.pdf` files (parsed with `pypdf`). Automatically rebuilds vector indices on file upload or deletion.
- **Intent Detection & Auto-Escalation**: Keyword classification for `billing`, `technical`, `account`, `complaint`, `urgent`, and `general` intents. Automatically escalates high-priority complaints or low RAG confidence queries to human support tickets.
- **Signature Reasoning UI**: Every assistant message visibly renders routing rationale—detected intent, confidence %, response latency in ms, RAG grounded status, and escalation triggers.
- **Role-Based Auth & Admin Console**: JWT authentication with direct `bcrypt` password hashing. The first account created automatically acquires the `admin` role. Features metrics dashboard (`recharts`) and live human escalation queue.

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, SQLite (swappable to PostgreSQL via `DATABASE_URL`), PyJWT, direct `bcrypt`, Scikit-learn, PyPDF, Uvicorn.
- **Frontend**: React 18, Vite, React Router v6, Recharts, Lucide React icons, Axios.
- **Containerization**: Docker, Docker Compose, Nginx.

---

## Quick Start (Zero-Setup Local Dev)

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server (defaults to LLM_PROVIDER=template)
uvicorn app.main:app --reload --port 8000
```
Backend server runs at `http://localhost:8000`. Interactive API Docs are available at `http://localhost:8000/docs`.

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install packages
npm install

# Start Vite development server
npm run dev
```
Frontend application runs at `http://localhost:5173`.

---

## LLM Provider Configuration & Provider Switching

The backend supports 4 pluggable LLM providers selected via the `LLM_PROVIDER` environment variable in `backend/.env`:

| Provider | `LLM_PROVIDER` | Requirements | Description |
| :--- | :--- | :--- | :--- |
| **Template (Default)** | `template` | None | Zero-setup canned responses and RAG context summarization. |
| **Ollama** | `ollama` | Local Ollama instance | Fully local, free LLM execution via Ollama API (`http://localhost:11434`). |
| **Anthropic** | `anthropic` | `ANTHROPIC_API_KEY` | Calls Claude 3.5 Messages API. |
| **OpenAI** | `openai` | `OPENAI_API_KEY` | Calls OpenAI Chat Completions API (`gpt-4o-mini`). |

### Setting up Ollama (Optional Local LLM)

1. Download and install Ollama from [ollama.com](https://ollama.com/).
2. Pull a model:
   ```bash
   ollama pull llama3.2
   ```
3. Set environment variable in `backend/.env`:
   ```env
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2
   ```
4. Restart backend server (`uvicorn app.main:app`). No code changes required!

---

## Running with Docker & Docker Compose

Deploy the entire stack with a single command:

```bash
docker-compose up --build
```

- **Frontend Application**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`

---

## API Endpoints Overview

### Authentication
- `POST /auth/signup` - Register user (`email`, `password`). First registered user becomes `admin`.
- `POST /auth/login` - Authenticate & obtain JWT bearer token.
- `GET /auth/me` - Retrieve authenticated user profile & role.

### Support Chat
- `GET /chat/conversations` - List current user's past conversations.
- `GET /chat/conversations/{id}` - Fetch conversation detail with complete message history.
- `DELETE /chat/conversations/{id}` - Delete conversation.
- `POST /chat/message` - Send message (`conversation_id`, `content`). Returns user & assistant messages with reasoning metrics.
- `POST /chat/resolve/{id}` - Mark conversation resolved.
- `POST /chat/feedback` - Submit thumbs up/down (`message_id`, `feedback: 1 | -1`).

### Knowledge Base (Admin Only)
- `POST /kb/upload` - Upload `.txt`, `.md`, or `.pdf` file. Rebuilds TF-IDF index.
- `GET /kb/documents` - List uploaded documents and chunk counts.
- `DELETE /kb/documents/{id}` - Delete document and refresh TF-IDF index.

### Metrics & Escalations (Admin Only)
- `GET /metrics/summary` - Aggregate metrics (Resolution %, Escalation %, Latency, CSAT %).
- `GET /tickets` - List human escalation ticket queue.
- `PATCH /tickets/{id}/status` - Update ticket status (`open` | `in_progress` | `closed`).

---

## Automated Smoke Testing

To run the automated end-to-end backend API test suite:

```bash
python backend/smoke_test.py
```

This verifies signup, login, role assignment, KB document uploading, RAG retrieval, intent classification, auto-escalation ticket creation, feedback submission, metrics calculation, and ticket resolution.

---

## Production Deployment Checklist

1. **CORS Hardening**: In `backend/app/main.py`, restrict `allow_origins` from `"*"` to your production frontend domain (e.g., `https://support.yourcompany.com`).
2. **Secret Keys**: Update `SECRET_KEY` in `backend/.env` to a cryptographically secure 64-character string.
3. **Database Migration**: Switch `DATABASE_URL` from SQLite to PostgreSQL (e.g., `postgresql://user:pass@host:5432/dbname`) without modifying any application logic.
4. **Ollama RAM Requirements**: If deploying Ollama on cloud servers (EC2, Render, DigitalOcean), ensure the host machine has at least 8GB to 16GB of dedicated RAM.
