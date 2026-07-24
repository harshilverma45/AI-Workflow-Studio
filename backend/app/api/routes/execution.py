from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.execution import Execution
from app.models.iteration import Iteration
from app.services.loop_engine import LoopEngine

router = APIRouter(tags=["execution"])


class ExecuteRequest(BaseModel):
    """Payload for creating a loop execution request."""

    prompt: str = Field(min_length=1, max_length=10_000)


class ExecuteResponse(BaseModel):
    """Response returned after an execution is persisted."""

    id: int
    prompt: str
    final_response: str
    iterations: int
    quality_score: float


@router.post("/execute", response_model=ExecuteResponse, status_code=status.HTTP_201_CREATED)
def execute_loop(payload: ExecuteRequest, database: Session = Depends(get_db)) -> ExecuteResponse:
    """Start a loop engineering execution for the provided prompt."""
    result = LoopEngine().run(payload.prompt)
    execution = Execution(
        prompt=payload.prompt,
        final_response=result["final_response"],
        iterations=result["iterations"],
    )
    database.add(execution)
    database.flush()

    for item in result["iteration_results"]:
        database.add(Iteration(execution_id=execution.id, **item))

    database.commit()
    database.refresh(execution)
    return ExecuteResponse(
        id=execution.id,
        prompt=execution.prompt,
        final_response=execution.final_response or "",
        iterations=execution.iterations,
        quality_score=result["quality_score"],
    )


@router.get("/executions")
def list_executions(database: Session = Depends(get_db)) -> list[dict[str, str | int]]:
    """Return previous runs."""
    executions = database.scalars(select(Execution).order_by(Execution.created_at.desc())).all()
    return [
        {
            "id": execution.id,
            "prompt": execution.prompt,
            "final_response": execution.final_response or "",
            "iterations": execution.iterations,
        }
        for execution in executions
    ]


@router.get("/execution/{execution_id}")
def get_execution(execution_id: int, database: Session = Depends(get_db)) -> dict[str, object]:
    """Return execution history for a specific run."""
    execution = database.get(Execution, execution_id)
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    iterations = database.scalars(
        select(Iteration)
        .where(Iteration.execution_id == execution_id)
        .order_by(Iteration.iteration_number)
    ).all()
    return {
        "id": execution.id,
        "prompt": execution.prompt,
        "final_response": execution.final_response or "",
        "iterations": execution.iterations,
        "history": [
            {
                "iteration_number": item.iteration_number,
                "prompt": item.prompt,
                "response": item.response or "",
                "evaluation": item.evaluation or "",
                "score": item.score,
            }
            for item in iterations
        ],
    }
