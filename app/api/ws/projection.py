from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.projection_manager import projection_manager

router = APIRouter()


@router.websocket("/ws/projection/{session_id}")
async def projection_websocket(
    websocket: WebSocket,
    session_id: int,
    role: str = Query(default="display"),
):
    await projection_manager.connect(session_id, websocket, role)
    try:
        while True:
            data = await websocket.receive_json()
            if role == "controller":
                await projection_manager.handle_command(session_id, data)
    except WebSocketDisconnect:
        await projection_manager.disconnect(session_id, websocket)
