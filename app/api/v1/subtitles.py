from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.subtitle import SubtitleFile
from app.schemas.subtitle import SubtitleFileResponse, SubtitleGenerateRequest

router = APIRouter()


@router.get("", response_model=list[SubtitleFileResponse])
async def list_subtitles(db: AsyncSession = Depends(get_db)):
    stmt = select(SubtitleFile).order_by(SubtitleFile.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{subtitle_id}", response_model=SubtitleFileResponse)
async def get_subtitle(subtitle_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(SubtitleFile)
        .where(SubtitleFile.id == subtitle_id)
        .options(selectinload(SubtitleFile.lines))
    )
    result = await db.execute(stmt)
    return result.scalar_one()


@router.get("/by-song/{song_id}", response_model=list[SubtitleFileResponse])
async def get_subtitles_by_song(song_id: int, db: AsyncSession = Depends(get_db)):
    """Get all subtitle files for a song, with lines eager-loaded."""
    stmt = (
        select(SubtitleFile)
        .where(SubtitleFile.song_id == song_id)
        .options(selectinload(SubtitleFile.lines))
        .order_by(SubtitleFile.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/generate", response_model=SubtitleFileResponse, status_code=201)
async def generate_subtitle(
    request: SubtitleGenerateRequest, db: AsyncSession = Depends(get_db)
):
    # TODO: Implement subtitle generation from lyrics
    raise NotImplementedError("Subtitle generation not yet implemented")
