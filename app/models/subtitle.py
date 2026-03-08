from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SubtitleFile(Base):
    __tablename__ = "subtitle_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id"))
    filename: Mapped[str] = mapped_column(String(255))
    format: Mapped[str] = mapped_column(String(10))  # srt, vtt, lrc, txt
    source: Mapped[str] = mapped_column(String(50))  # manual, whisper, imported
    file_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    # Lyrics alignment metadata
    alignment_source: Mapped[str | None] = mapped_column(String(50))  # "syncedlyrics" | None
    alignment_confidence: Mapped[float | None] = mapped_column(Float)
    alignment_matched: Mapped[int | None] = mapped_column(Integer)
    alignment_total: Mapped[int | None] = mapped_column(Integer)
    alignment_algorithm: Mapped[str | None] = mapped_column(String(20))  # anchor | greedy_fallback

    song: Mapped["Song | None"] = relationship(back_populates="subtitle_files")
    lines: Mapped[list["SubtitleLine"]] = relationship(
        back_populates="subtitle_file", cascade="all, delete-orphan"
    )


class SubtitleLine(Base):
    __tablename__ = "subtitle_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    subtitle_file_id: Mapped[int] = mapped_column(ForeignKey("subtitle_files.id"))
    index: Mapped[int]
    start_ms: Mapped[int]
    end_ms: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    text_secondary: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    source_type: Mapped[str | None] = mapped_column(String(20))  # anchor|interpolated|extrapolated|phantom

    subtitle_file: Mapped["SubtitleFile"] = relationship(back_populates="lines")


from app.models.song import Song  # noqa: E402, F401
