from __future__ import annotations

from collections import defaultdict
from queue import Queue
from threading import Lock


class ExecutionSocketManager:
    """Coordinate ordered live execution events across WebSocket subscribers."""

    def __init__(self) -> None:
        self._events: dict[int, list[dict[str, object]]] = defaultdict(list)
        self._subscribers: dict[int, list[Queue[dict[str, object]]]] = defaultdict(list)
        self._live_executions: set[int] = set()
        self._lock = Lock()

    def start(self, execution_id: int) -> None:
        """Mark an execution as live before its background task begins."""
        with self._lock:
            self._live_executions.add(execution_id)

    def is_live(self, execution_id: int) -> bool:
        """Return whether an execution is managed by the current process."""
        with self._lock:
            return execution_id in self._live_executions

    def publish(self, execution_id: int, event: dict[str, object]) -> None:
        """Store an event and immediately distribute it to every subscriber."""
        with self._lock:
            self._events[execution_id].append(event)
            for subscriber in self._subscribers[execution_id]:
                subscriber.put(event)

            if event["type"] in {"execution_completed", "execution_failed"}:
                self._live_executions.discard(execution_id)

    def subscribe(self, execution_id: int) -> tuple[Queue[dict[str, object]], list[dict[str, object]], bool]:
        """Register a subscriber and return any events emitted before it connected."""
        with self._lock:
            subscriber: Queue[dict[str, object]] = Queue()
            self._subscribers[execution_id].append(subscriber)
            return subscriber, list(self._events[execution_id]), execution_id in self._live_executions

    def unsubscribe(self, execution_id: int, subscriber: Queue[dict[str, object]]) -> None:
        """Remove a disconnected WebSocket subscriber."""
        with self._lock:
            subscribers = self._subscribers.get(execution_id, [])
            if subscriber in subscribers:
                subscribers.remove(subscriber)


execution_socket_manager = ExecutionSocketManager()
