# AI Workflow Studio

A visual platform for exploring Loop Engineering and iterative AI agent workflows.

## Stack

- Backend: FastAPI, SQLAlchemy, LangGraph, LangChain, WebSockets
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

## Current phase

Phase 1 scaffold is now in place with a lightweight FastAPI API, SQLite models, and a React/Vite starter UI.
