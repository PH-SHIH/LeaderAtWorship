from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.subtitle import SubtitleFile, SubtitleLine
from app.schemas.subtitle import (
    SubtitleFileResponse,
    SubtitleLineCreate,
    SubtitleLineResponse,
    SubtitleLineUpdate,
)

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


# ── Subtitle Line CRUD ──────────────────────────────────────


@router.patch("/lines/{line_id}", response_model=SubtitleLineResponse)
async def update_line(
    line_id: int, update: SubtitleLineUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a single subtitle line's text or timing."""
    line = await db.get(SubtitleLine, line_id)
    if not line:
        raise HTTPException(status_code=404, detail="Subtitle line not found")

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(line, field, value)

    # Mark as manually edited
    line.source_type = "manual"

    await db.flush()
    await db.refresh(line)
    return line


@router.post("/{subtitle_id}/lines", response_model=SubtitleLineResponse, status_code=201)
async def create_line(
    subtitle_id: int, line_in: SubtitleLineCreate, db: AsyncSession = Depends(get_db)
):
    """Insert a new subtitle line and re-index subsequent lines."""
    sub_file = await db.get(SubtitleFile, subtitle_id)
    if not sub_file:
        raise HTTPException(status_code=404, detail="Subtitle file not found")

    # Shift existing lines at or after the insert position
    stmt = (
        select(SubtitleLine)
        .where(SubtitleLine.subtitle_file_id == subtitle_id)
        .where(SubtitleLine.index >= line_in.index)
        .order_by(SubtitleLine.index.desc())
    )
    result = await db.execute(stmt)
    for existing in result.scalars().all():
        existing.index += 1

    new_line = SubtitleLine(
        subtitle_file_id=subtitle_id,
        index=line_in.index,
        start_ms=line_in.start_ms,
        end_ms=line_in.end_ms,
        text=line_in.text,
        source_type="manual",
    )
    db.add(new_line)
    await db.flush()
    await db.refresh(new_line)
    return new_line


@router.delete("/lines/{line_id}", status_code=204)
async def delete_line(line_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a subtitle line and re-index remaining lines."""
    line = await db.get(SubtitleLine, line_id)
    if not line:
        raise HTTPException(status_code=404, detail="Subtitle line not found")

    subtitle_file_id = line.subtitle_file_id
    deleted_index = line.index
    await db.delete(line)
    await db.flush()

    # Re-index lines after the deleted one
    stmt = (
        select(SubtitleLine)
        .where(SubtitleLine.subtitle_file_id == subtitle_file_id)
        .where(SubtitleLine.index > deleted_index)
        .order_by(SubtitleLine.index)
    )
    result = await db.execute(stmt)
    for remaining in result.scalars().all():
        remaining.index -= 1
