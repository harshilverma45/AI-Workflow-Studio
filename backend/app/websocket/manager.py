from collections.abc import AsyncGenerator


class ExecutionSocketManager:
    """Placeholder WebSocket manager for live execution updates."""

    async def stream(self, execution_id: int) -> AsyncGenerator[str, None]:
        """Yield a simple progress message for the given execution."""
        yield f"Execution {execution_id} started"
