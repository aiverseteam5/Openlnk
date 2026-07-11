"""WebSocket sync service — real-time commitment state (OL-003, OL-003a).

ConnectionManager handles per-context WebSocket subscriptions.
Delta replay is bounded: <= 200 events or <= 30 days (OL-003a).
"""

from collections import deque
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from fastapi import WebSocket

from app.schemas import DeltaEvent

logger = structlog.get_logger()

# OL-003a: replay window bounds
REPLAY_MAX_EVENTS = 200
REPLAY_MAX_DAYS = 30


class ConnectionManager:
    """Manages WebSocket connections per context.

    In-memory for single-process; scale-out via Redis pubsub (Gate 2).
    """

    def __init__(self) -> None:
        # context_id → set of active WebSocket connections
        self._connections: dict[UUID, set[WebSocket]] = {}
        # context_id → bounded deque of (timestamp, DeltaEvent)
        self._replay_buffer: dict[UUID, deque[tuple[datetime, DeltaEvent]]] = {}

    async def connect(self, websocket: WebSocket, context_id: UUID) -> None:
        """Accept and register a WebSocket connection for a context."""
        await websocket.accept()
        if context_id not in self._connections:
            self._connections[context_id] = set()
        self._connections[context_id].add(websocket)
        logger.info("ws_connected", context_id=str(context_id))

    def disconnect(self, websocket: WebSocket, context_id: UUID) -> None:
        """Remove a WebSocket connection."""
        if context_id in self._connections:
            self._connections[context_id].discard(websocket)
            if not self._connections[context_id]:
                del self._connections[context_id]

    async def broadcast_to_context(self, context_id: UUID, event: DeltaEvent) -> None:
        """Broadcast a delta event to all subscribers of a context."""
        # Store in replay buffer
        if context_id not in self._replay_buffer:
            self._replay_buffer[context_id] = deque(maxlen=REPLAY_MAX_EVENTS)
        self._replay_buffer[context_id].append((datetime.now(UTC), event))

        # Broadcast to connected clients
        if context_id not in self._connections:
            return

        dead: list[WebSocket] = []
        for ws in self._connections[context_id]:
            try:
                await ws.send_json(event.model_dump())
            except Exception:
                dead.append(ws)

        for ws in dead:
            self._connections[context_id].discard(ws)

    def get_replay_events(self, context_id: UUID, *, since_seq: int = 0) -> list[DeltaEvent]:
        """Return buffered events for replay, bounded by OL-003a.

        Returns events with seq > since_seq, within the 30-day window,
        capped at 200 events.
        """
        if context_id not in self._replay_buffer:
            return []

        cutoff = datetime.now(UTC) - timedelta(days=REPLAY_MAX_DAYS)
        events = [
            event
            for ts, event in self._replay_buffer[context_id]
            if ts >= cutoff and event.seq > since_seq
        ]
        return events[:REPLAY_MAX_EVENTS]


# Singleton for the application
manager = ConnectionManager()
