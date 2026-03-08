from pydantic import BaseModel


class ProjectionSessionCreate(BaseModel):
    flow_id: int | None = None


class ProjectionState(BaseModel):
    session_id: int
    flow_id: int | None = None
    current_item_index: int = 0
    current_line_index: int = 0
    is_blank: bool = False
    current_text: str = ""
    current_text_secondary: str = ""


class AudioExtractRequest(BaseModel):
    url: str
    whisper_model: str | None = None


class TaskResponse(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    error: str | None = None
    result_id: int | None = None
    video_title: str | None = None
    detail: str | None = None
