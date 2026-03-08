from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectionSession(Base):
    __tablename__ = "projection_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    flow_id: Mapped[int | None] = mapped_column(ForeignKey("worship_flows.id"))
    current_item_index: Mapped[int] = mapped_column(default=0)
    current_line_index: Mapped[int] = mapped_column(default=0)
    is_live: Mapped[bool] = mapped_column(default=False)
    is_blank: Mapped[bool] = mapped_column(default=False)
    started_at: Mapped[datetime | None]
    ended_at: Mapped[datetime | None]
