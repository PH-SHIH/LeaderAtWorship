from dataclasses import asdict, dataclass, field

from fastapi import WebSocket


@dataclass
class ProjectionState:
    session_id: int
    flow_id: int | None = None
    current_item_index: int = 0
    current_line_index: int = 0
    is_blank: bool = False
    current_text: str = ""
    current_text_secondary: str = ""


class ProjectionManager:
    """Manages WebSocket connections and projection state per session."""

    def __init__(self):
        self._connections: dict[int, set[WebSocket]] = {}
        self._state: dict[int, ProjectionState] = {}

    async def connect(self, session_id: int, websocket: WebSocket, role: str):
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = set()
            self._state[session_id] = ProjectionState(session_id=session_id)
        self._connections[session_id].add(websocket)

        # Send current state to newly connected client
        await websocket.send_json(
            {"type": "state_sync", "data": asdict(self._state[session_id])}
        )

    async def disconnect(self, session_id: int, websocket: WebSocket):
        self._connections.get(session_id, set()).discard(websocket)

    async def broadcast(self, session_id: int, message: dict):
        dead = []
        for ws in self._connections.get(session_id, set()):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[session_id].discard(ws)

    async def handle_command(self, session_id: int, command: dict):
        state = self._state.get(session_id)
        if not state:
            return

        action = command.get("action")
        if action == "next_line":
            state.current_line_index += 1
        elif action == "prev_line":
            state.current_line_index = max(0, state.current_line_index - 1)
        elif action == "goto_line":
            state.current_line_index = command.get("index", 0)
        elif action == "next_item":
            state.current_item_index += 1
            state.current_line_index = 0
        elif action == "prev_item":
            state.current_item_index = max(0, state.current_item_index - 1)
            state.current_line_index = 0
        elif action == "toggle_blank":
            state.is_blank = not state.is_blank
        elif action == "set_text":
            state.current_text = command.get("text", "")
            state.current_text_secondary = command.get("text_secondary", "")

        await self.broadcast(
            session_id, {"type": "state_update", "data": asdict(state)}
        )


projection_manager = ProjectionManager()
