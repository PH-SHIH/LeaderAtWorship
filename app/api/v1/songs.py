from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.song import Song, SongLyrics
from app.schemas.song import (
    LyricsCreate,
    LyricsResponse,
    SongCreate,
    SongListResponse,
    SongResponse,
    SongUpdate,
)

router = APIRouter()


@router.get("", response_model=list[SongListResponse])
async def list_songs(
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Song).order_by(Song.title)
    if q:
        stmt = stmt.where(Song.title.icontains(q))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=SongResponse, status_code=201)
async def create_song(song_in: SongCreate, db: AsyncSession = Depends(get_db)):
    song = Song(**song_in.model_dump())
    db.add(song)
    await db.flush()
    await db.refresh(song, attribute_names=["lyrics"])
    return song


@router.get("/{song_id}", response_model=SongResponse)
async def get_song(song_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Song).where(Song.id == song_id).options(selectinload(Song.lyrics))
    result = await db.execute(stmt)
    song = result.scalar_one()
    return song


@router.put("/{song_id}", response_model=SongResponse)
async def update_song(
    song_id: int, song_in: SongUpdate, db: AsyncSession = Depends(get_db)
):
    stmt = select(Song).where(Song.id == song_id)
    result = await db.execute(stmt)
    song = result.scalar_one()
    for key, value in song_in.model_dump(exclude_unset=True).items():
        setattr(song, key, value)
    await db.flush()
    await db.refresh(song, attribute_names=["lyrics"])
    return song


@router.delete("/{song_id}", status_code=204)
async def delete_song(song_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Song).where(Song.id == song_id)
    result = await db.execute(stmt)
    song = result.scalar_one()
    await db.delete(song)


@router.post("/{song_id}/lyrics", response_model=LyricsResponse, status_code=201)
async def add_lyrics(
    song_id: int, lyrics_in: LyricsCreate, db: AsyncSession = Depends(get_db)
):
    lyrics = SongLyrics(song_id=song_id, **lyrics_in.model_dump())
    db.add(lyrics)
    await db.flush()
    return lyrics
