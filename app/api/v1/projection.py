from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.session import ProjectionSession
from app.schemas.projection import ProjectionSessionCreate

router = APIRouter()


@router.post("/sessions", status_code=201)
async def create_session(
    session_in: ProjectionSessionCreate, db: AsyncSession = Depends(get_db)
):
    session = ProjectionSession(flow_id=session_in.flow_id, is_live=True)
    db.add(session)
    await db.flush()
    return {"id": session.id, "flow_id": session.flow_id, "is_live": True}
