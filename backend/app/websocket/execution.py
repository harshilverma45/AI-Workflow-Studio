import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.execution import Execution
from app.models.iteration import Iteration
from app.websocket.manager import execution_socket_manager

router = APIRouter(tags=["websocket"])


async def execution_events(execution_id: int) -> AsyncGenerator[dict[str, object], None]:
    """Yield structured progress events for a persisted execution."""
    database = SessionLocal()
    try:
        execution = database.get(Execution, execution_id)
        if execution is None:
            return

        yield {
            "type": "execution_started",
            "execution_id": execution.id,
            "prompt": execution.prompt,
        }
        iterations = database.scalars(
            select(Iteration)
            .where(Iteration.execution_id == execution_id)
            .order_by(Iteration.iteration_number)
        ).all()
        for iteration in iterations:
            yield {
                "type": "iteration_completed",
                "execution_id": execution.id,
                "iteration_number": iteration.iteration_number,
                "response": iteration.response or "",
                "evaluation": iteration.evaluation or "",
                "score": iteration.score,
            }
        yield {
            "type": "execution_completed",
            "execution_id": execution.id,
            "iterations": execution.iterations,
            "final_response": execution.final_response or "",
        }
    finally:
        database.close()


@router.websocket("/ws/execution/{execution_id}")
async def stream_execution(websocket: WebSocket, execution_id: int) -> None:
    """Stream live progress, or replay the history of a completed execution."""
    await websocket.accept()
    database = SessionLocal()
    if execution_socket_manager.is_live(execution_id):
        subscriber, events, is_live = execution_socket_manager.subscribe(execution_id)
        try:
            for event in events:
                await websocket.send_text(json.dumps(event))
            if is_live:
                while True:
                    event = await asyncio.to_thread(subscriber.get)
                    await websocket.send_text(json.dumps(event))
                    if event["type"] in {"execution_completed", "execution_failed"}:
                        return
        except WebSocketDisconnect:
            return
        finally:
            execution_socket_manager.unsubscribe(execution_id, subscriber)
            await websocket.close()
        return

    try:
        if database.get(Execution, execution_id) is None:
            await websocket.close(code=1008, reason="Execution not found")
            return
    finally:
        database.close()

    try:
        async for event in execution_events(execution_id):
            await websocket.send_text(json.dumps(event))
    except WebSocketDisconnect:
        return
    finally:
        await websocket.close()
