from fastapi import FastAPI

from app.api.routes import execution
from app.core.config import settings
from app.db.database import create_db_and_tables

app = FastAPI(title="AI Workflow Studio", version="0.1.0")

app.include_router(execution.router, prefix="/api")


@app.on_event("startup")
def startup() -> None:
    """Initialize database and other startup dependencies."""
    create_db_and_tables()


@app.get("/")
def read_root() -> dict[str, str]:
    """Health check endpoint."""
    return {"message": "AI Workflow Studio API is running", "project": settings.project_name}
