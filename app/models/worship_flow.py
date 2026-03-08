from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WorshipFlow(Base):
    __tablename__ = "worship_flows"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    date: Mapped[date | None]
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    items: Mapped[list["FlowItem"]] = relationship(
        back_populates="flow", order_by="FlowItem.position", cascade="all, delete-orphan"
    )


class FlowItem(Base):
    __tablename__ = "flow_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    flow_id: Mapped[int] = mapped_column(ForeignKey("worship_flows.id"))
    song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id"))
    position: Mapped[int]
    item_type: Mapped[str] = mapped_column(String(50))  # song, prayer, reading, announcement
    label: Mapped[str | None] = mapped_column(String(255))
    transition_note: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int | None]

    flow: Mapped["WorshipFlow"] = relationship(back_populates="items")
    song: Mapped["Song | None"] = relationship()


from app.models.song import Song  # noqa: E402, F401
