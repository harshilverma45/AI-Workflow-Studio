import json

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.websocket.manager import ExecutionSocketManager


def test_live_event_manager_delivers_events_in_order() -> None:
    """Subscribers receive each event while an execution is live."""
    manager = ExecutionSocketManager()
    manager.start(1)
    subscriber, history, is_live = manager.subscribe(1)

    manager.publish(1, {"type": "execution_started", "execution_id": 1})
    manager.publish(1, {"type": "execution_completed", "execution_id": 1})

    assert history == []
    assert is_live is True
    assert subscriber.get()["type"] == "execution_started"
    assert subscriber.get()["type"] == "execution_completed"
    assert manager.is_live(1) is False


def test_execution_websocket_replays_persisted_progress() -> None:
    """The execution WebSocket sends ordered progress events for a stored run."""
    settings.model_provider = "local"
    client = TestClient(app)
    created = client.post("/api/execute", json={"prompt": "Test WebSocket progress"})
    execution_id = created.json()["id"]

    with client.websocket_connect(f"/ws/execution/{execution_id}") as websocket:
        events = [json.loads(websocket.receive_text()) for _ in range(3)]

    assert [event["type"] for event in events] == [
        "execution_started",
        "iteration_completed",
        "execution_completed",
    ]
    assert events[1]["iteration_number"] == 1
    assert events[2]["execution_id"] == execution_id


def test_live_execution_streams_events_and_persists_iterations() -> None:
    """The live endpoint streams loop progress while persisting its completed state."""
    settings.model_provider = "local"
    client = TestClient(app)
    started = client.post("/api/execute/live", json={"prompt": "Test live progress"})

    assert started.status_code == 202
    execution_id = started.json()["id"]
    with client.websocket_connect(f"/ws/execution/{execution_id}") as websocket:
        events = [json.loads(websocket.receive_text()) for _ in range(3)]

    assert [event["type"] for event in events] == [
        "execution_started",
        "iteration_completed",
        "execution_completed",
    ]
    history = client.get(f"/api/execution/{execution_id}")
    assert history.status_code == 200
    assert len(history.json()["history"]) == 1


def test_missing_execution_websocket_closes_with_policy_error() -> None:
    """Unknown executions should not produce a progress stream."""
    client = TestClient(app)

    with client.websocket_connect("/ws/execution/999999") as websocket:
        try:
            websocket.receive_text()
        except Exception as error:
            assert getattr(error, "code", None) == 1008
