from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Song(Base):
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    artist: Mapped[str | None] = mapped_column(String(255))
    key_signature: Mapped[str | None] = mapped_column(String(10))
    tempo_bpm: Mapped[int | None]
    tags: Mapped[str | None] = mapped_column(Text)
    audio_path: Mapped[str | None] = mapped_column(String(500))
    vocals_path: Mapped[str | None] = mapped_column(String(500))
    accompaniment_path: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    lyrics: Mapped[list["SongLyrics"]] = relationship(
        back_populates="song", cascade="all, delete-orphan"
    )
    subtitle_files: Mapped[list["SubtitleFile"]] = relationship(back_populates="song")


class SongLyrics(Base):
    __tablename__ = "song_lyrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"))
    language: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(default=False)

    song: Mapped["Song"] = relationship(back_populates="lyrics")
    lines: Mapped[list["LyricsLine"]] = relationship(
        back_populates="lyrics", cascade="all, delete-orphan"
    )


class LyricsLine(Base):
    __tablename__ = "lyrics_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    lyrics_id: Mapped[int] = mapped_column(ForeignKey("song_lyrics.id"))
    line_number: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    section_label: Mapped[str | None] = mapped_column(String(50))

    lyrics: Mapped["SongLyrics"] = relationship(back_populates="lines")


# Avoid circular import - use string reference
from app.models.subtitle import SubtitleFile  # noqa: E402, F401
