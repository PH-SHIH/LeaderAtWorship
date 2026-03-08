from dataclasses import asdict, dataclass, field

from fastapi import WebSocket


@dataclass
class SubtitleLineData:
    text: str = ""
    text_secondary: str = ""
    start_ms: int = 0


@dataclass
class FlowItemData:
    item_type: str = "song"
    label: str = ""
    song_id: int | None = None
    lines: list[SubtitleLineData] = field(default_factory=list)


@dataclass
class ProjectionState:
    session_id: int
    flow_id: int | None = None
    current_item_index: int = 0
    current_line_index: int = 0
    is_blank: bool = False
    current_text: str = ""
    current_text_secondary: str = ""
    items: list[dict] = field(default_factory=list)  # serializable item info
    total_items: int = 0
    total_lines: int = 0  # lines in current item
    current_item_label: str = ""
    current_item_lines: list[dict] = field(default_factory=list)  # [{text, text_secondary}]
    current_song_id: int | None = None  # song_id for audio streaming


class ProjectionManager:
    """Manages WebSocket connections and projection state per session."""

    def __init__(self):
        self._connections: dict[int, set[WebSocket]] = {}
        self._state: dict[int, ProjectionState] = {}
        self._flow_data: dict[int, list[FlowItemData]] = {}

    def load_flow_data(self, session_id: int, flow_id: int | None, items: list[FlowItemData]):
        """Load pre-fetched flow data into the manager."""
        self._flow_data[session_id] = items
        state = self._state.get(session_id)
        if state:
            state.flow_id = flow_id
            state.items = [
                {"label": it.label, "item_type": it.item_type, "song_id": it.song_id, "line_count": len(it.lines)}
                for it in items
            ]
            state.total_items = len(items)
            self._resolve_text(session_id)

    def _resolve_text(self, session_id: int):
        """Resolve current_text from flow data based on indices."""
        state = self._state.get(session_id)
        items = self._flow_data.get(session_id, [])
        if not state or not items:
            return

        item_idx = state.current_item_index
        if item_idx < 0 or item_idx >= len(items):
            state.current_text = ""
            state.current_text_secondary = ""
            state.current_item_label = ""
            state.total_lines = 0
            state.current_item_lines = []
            return

        item = items[item_idx]
        state.current_item_label = item.label
        state.current_song_id = item.song_id
        state.total_lines = len(item.lines)
        state.current_item_lines = [
            {"text": l.text, "text_secondary": l.text_secondary, "start_ms": l.start_ms}
            for l in item.lines
        ]

        line_idx = state.current_line_index
        if line_idx < 0 or line_idx >= len(item.lines):
            state.current_text = ""
            state.current_text_secondary = ""
            return

        line = item.lines[line_idx]
        state.current_text = line.text
        state.current_text_secondary = line.text_secondary

    async def connect(self, session_id: int, websocket: WebSocket, role: str):
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = set()
        if session_id not in self._state:
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

        items = self._flow_data.get(session_id, [])
        action = command.get("action")

        if action == "next_line":
            # If we have flow data, clamp to line count
            if items:
                item_idx = state.current_item_index
                if 0 <= item_idx < len(items):
                    max_line = len(items[item_idx].lines) - 1
                    if state.current_line_index < max_line:
                        state.current_line_index += 1
                    # else stay at last line
            else:
                state.current_line_index += 1

        elif action == "prev_line":
            state.current_line_index = max(0, state.current_line_index - 1)

        elif action == "goto_line":
            state.current_line_index = command.get("index", 0)

        elif action == "next_item":
            if items:
                if state.current_item_index < len(items) - 1:
                    state.current_item_index += 1
                    state.current_line_index = 0
            else:
                state.current_item_index += 1
                state.current_line_index = 0

        elif action == "prev_item":
            state.current_item_index = max(0, state.current_item_index - 1)
            state.current_line_index = 0

        elif action == "goto_item":
            idx = command.get("index", 0)
            if 0 <= idx < len(items) if items else True:
                state.current_item_index = idx
                state.current_line_index = 0

        elif action == "toggle_blank":
            state.is_blank = not state.is_blank

        elif action == "set_text":
            state.current_text = command.get("text", "")
            state.current_text_secondary = command.get("text_secondary", "")
            # Skip resolve when manually setting text
            await self.broadcast(
                session_id, {"type": "state_update", "data": asdict(state)}
            )
            return

        # Resolve text from flow data
        if items:
            self._resolve_text(session_id)

        await self.broadcast(
            session_id, {"type": "state_update", "data": asdict(state)}
        )


projection_manager = ProjectionManager()
