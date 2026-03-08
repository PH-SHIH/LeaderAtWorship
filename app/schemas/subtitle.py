from datetime import datetime

from pydantic import BaseModel


class SubtitleLineResponse(BaseModel):
    index: int
    start_ms: int
    end_ms: int
    text: str
    text_secondary: str | None = None
    confidence: float | None = None
    source_type: str | None = None

    model_config = {"from_attributes": True}


class SubtitleFileResponse(BaseModel):
    id: int
    song_id: int | None
    filename: str
    format: str
    source: str
    created_at: datetime
    alignment_source: str | None = None
    alignment_confidence: float | None = None
    alignment_matched: int | None = None
    alignment_total: int | None = None
    alignment_algorithm: str | None = None
    lines: list[SubtitleLineResponse] = []

    model_config = {"from_attributes": True}


class SubtitleGenerateRequest(BaseModel):
    song_id: int
    lyrics_id: int
    format: str = "srt"
