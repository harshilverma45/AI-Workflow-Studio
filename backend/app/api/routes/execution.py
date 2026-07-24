from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, get_db
from app.models.execution import Execution
from app.models.iteration import Iteration
from app.services.loop_engine import LoopEngine
from app.websocket.manager import execution_socket_manager

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


class LiveExecuteResponse(BaseModel):
    """Response returned immediately after a live execution is scheduled."""

    id: int
    prompt: str


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


def run_live_execution(execution_id: int, prompt: str) -> None:
    """Run and persist one execution while publishing each completed iteration."""
    database = SessionLocal()
    try:
        execution_socket_manager.publish(
            execution_id,
            {"type": "execution_started", "execution_id": execution_id, "prompt": prompt},
        )

        def persist_iteration(item: dict[str, object]) -> None:
            database.add(Iteration(execution_id=execution_id, **item))
            database.commit()
            execution_socket_manager.publish(
                execution_id,
                {
                    "type": "iteration_completed",
                    "execution_id": execution_id,
                    "iteration_number": item["iteration_number"],
                    "response": item["response"],
                    "evaluation": item["evaluation"],
                    "score": item["score"],
                },
            )

        result = LoopEngine().run(prompt, on_iteration=persist_iteration)
        execution = database.get(Execution, execution_id)
        if execution is None:
            raise RuntimeError("Live execution was not found.")
        execution.final_response = str(result["final_response"])
        execution.iterations = int(result["iterations"])
        database.commit()
        execution_socket_manager.publish(
            execution_id,
            {
                "type": "execution_completed",
                "execution_id": execution_id,
                "iterations": result["iterations"],
                "final_response": result["final_response"],
            },
        )
    except Exception as error:
        database.rollback()
        execution_socket_manager.publish(
            execution_id,
            {"type": "execution_failed", "execution_id": execution_id, "detail": str(error)},
        )
    finally:
        database.close()


@router.post("/execute/live", response_model=LiveExecuteResponse, status_code=status.HTTP_202_ACCEPTED)
def start_live_execution(
    payload: ExecuteRequest,
    background_tasks: BackgroundTasks,
    database: Session = Depends(get_db),
) -> LiveExecuteResponse:
    """Create an execution and return before its loop begins running."""
    execution = Execution(prompt=payload.prompt, iterations=0)
    database.add(execution)
    database.commit()
    database.refresh(execution)
    execution_socket_manager.start(execution.id)
    background_tasks.add_task(run_live_execution, execution.id, execution.prompt)
    return LiveExecuteResponse(id=execution.id, prompt=execution.prompt)


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
