from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.worship_flow import WorshipFlow


async def get_flow_with_songs(db: AsyncSession, flow_id: int) -> WorshipFlow:
    """Get a worship flow with all items and their associated songs."""
    stmt = (
        select(WorshipFlow)
        .where(WorshipFlow.id == flow_id)
        .options(selectinload(WorshipFlow.items))
    )
    result = await db.execute(stmt)
    return result.scalar_one()
