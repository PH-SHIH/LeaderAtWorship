from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.song import Song


async def search_songs(db: AsyncSession, query: str, language: str | None = None):
    """Search songs by title or lyrics content."""
    stmt = select(Song).where(Song.title.icontains(query))
    result = await db.execute(stmt)
    return result.scalars().all()
