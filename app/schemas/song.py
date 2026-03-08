from datetime import datetime

from pydantic import BaseModel


class SongBase(BaseModel):
    title: str
    artist: str | None = None
    key_signature: str | None = None
    tempo_bpm: int | None = None
    tags: str | None = None


class SongCreate(SongBase):
    pass


class SongUpdate(BaseModel):
    title: str | None = None
    artist: str | None = None
    key_signature: str | None = None
    tempo_bpm: int | None = None
    tags: str | None = None


class LyricsCreate(BaseModel):
    language: str = "zh"
    content: str
    is_primary: bool = False


class LyricsResponse(BaseModel):
    id: int
    language: str
    content: str
    is_primary: bool

    model_config = {"from_attributes": True}


class SongResponse(SongBase):
    id: int
    audio_path: str | None = None
    vocals_path: str | None = None
    accompaniment_path: str | None = None
    created_at: datetime
    updated_at: datetime
    lyrics: list[LyricsResponse] = []

    model_config = {"from_attributes": True}


class SongListResponse(BaseModel):
    id: int
    title: str
    artist: str | None
    key_signature: str | None

    model_config = {"from_attributes": True}
