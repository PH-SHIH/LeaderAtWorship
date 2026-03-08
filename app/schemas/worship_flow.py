from __future__ import annotations

import datetime

from pydantic import BaseModel


class FlowItemBase(BaseModel):
    song_id: int | None = None
    position: int
    item_type: str = "song"
    label: str | None = None
    transition_note: str | None = None
    duration_seconds: int | None = None


class FlowItemCreate(FlowItemBase):
    pass


class FlowItemResponse(FlowItemBase):
    id: int
    song_title: str | None = None

    model_config = {"from_attributes": True}


class FlowCreate(BaseModel):
    name: str
    date: datetime.date | None = None
    notes: str | None = None
    items: list[FlowItemCreate] = []


class FlowUpdate(BaseModel):
    name: str | None = None
    date: datetime.date | None = None
    notes: str | None = None
    items: list[FlowItemCreate] | None = None


class FlowResponse(BaseModel):
    id: int
    name: str
    date: datetime.date | None = None
    notes: str | None = None
    created_at: datetime.datetime
    items: list[FlowItemResponse] = []

    model_config = {"from_attributes": True}
