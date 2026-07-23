from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["execution"])


class ExecuteRequest(BaseModel):
    """Payload for creating a loop execution request."""

    prompt: str


@router.post("/execute")
def execute_loop(payload: ExecuteRequest) -> dict[str, str | int]:
    """Start a loop engineering execution for the provided prompt."""
    return {
        "message": "Execution started",
        "iterations": 1,
        "prompt": payload.prompt,
    }


@router.get("/executions")
def list_executions() -> list[dict[str, str | int]]:
    """Return previous runs."""
    return []


@router.get("/execution/{execution_id}")
def get_execution(execution_id: int) -> dict[str, str | int]:
    """Return execution history for a specific run."""
    return {"execution_id": execution_id, "status": "pending"}
