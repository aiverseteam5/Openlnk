"""WebSocket sync endpoint (OL-003).

Real-time commitment state sync via per-context WebSocket connections.
"""

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.sync import manager

router = APIRouter(tags=["sync"])


@router.websocket("/ws/{context_id}")
async def websocket_sync(websocket: WebSocket, context_id: UUID) -> None:
    """WebSocket endpoint for real-time context sync.

    Clients connect per context_id and receive DeltaEvents
    for all commitment changes within that context.
    """
    await manager.connect(websocket, context_id)
    try:
        while True:
            # Keep connection alive; client sends pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, context_id)
