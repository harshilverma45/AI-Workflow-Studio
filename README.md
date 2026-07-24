# AI Workflow Studio

A visual platform for exploring Loop Engineering and iterative AI agent workflows.

## Stack

- Backend: FastAPI, SQLAlchemy, LangGraph, LangChain, WebSockets, Gemini
- Frontend: React, Vite, Tailwind CSS, React Flow

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project status

Phase 1 is complete: execution API, SQLite persistence, live WebSocket iteration
updates, a readable refinement timeline, and execution history are working. The next
phase is cross-run AI memory and, later, execution comparison. The planned AI provider
is Gemini using its available free API tier. OpenAI and Ollama are not required for
this project.

## Gemini provider

Create a Gemini API key through Google AI Studio, then set these values in `backend/.env`:

```powershell
MODEL_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-3.6-flash
```

Gemini free-tier quotas and model availability are controlled by Google and can change. The application does not require a paid account.

## Offline fallback

```env
MODEL_PROVIDER=local
```

Use the offline fallback for API and database tests without an API key.
