from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.session import ProjectionSession
from app.models.subtitle import SubtitleFile, SubtitleLine
from app.models.worship_flow import FlowItem, WorshipFlow
from app.schemas.projection import ProjectionSessionCreate
from app.services.projection_manager import (
    FlowItemData,
    ProjectionState,
    SubtitleLineData,
    projection_manager,
)

router = APIRouter()


@router.post("/sessions", status_code=201)
async def create_session(
    session_in: ProjectionSessionCreate, db: AsyncSession = Depends(get_db)
):
    session = ProjectionSession(flow_id=session_in.flow_id, is_live=True)
    db.add(session)
    await db.flush()

    # Pre-load flow data if a flow_id is provided
    flow_items: list[FlowItemData] = []
    if session_in.flow_id:
        stmt = (
            select(WorshipFlow)
            .where(WorshipFlow.id == session_in.flow_id)
            .options(
                selectinload(WorshipFlow.items).selectinload(FlowItem.song)
            )
        )
        result = await db.execute(stmt)
        flow = result.scalar_one_or_none()

        if flow:
            for item in flow.items:
                label = ""
                if item.song:
                    label = item.song.title
                elif item.label:
                    label = item.label
                else:
                    label = item.item_type

                lines: list[SubtitleLineData] = []

                # Load subtitles for song items
                if item.song_id:
                    sub_stmt = (
                        select(SubtitleFile)
                        .where(SubtitleFile.song_id == item.song_id)
                        .options(selectinload(SubtitleFile.lines))
                        .order_by(SubtitleFile.created_at.desc())
                        .limit(1)
                    )
                    sub_result = await db.execute(sub_stmt)
                    sub_file = sub_result.scalar_one_or_none()

                    if sub_file:
                        sorted_lines = sorted(sub_file.lines, key=lambda l: l.index)
                        for sl in sorted_lines:
                            lines.append(SubtitleLineData(
                                text=sl.text or "",
                                text_secondary=sl.text_secondary or "",
                            ))

                # Non-song items get a single "title" line
                if not lines and not item.song_id:
                    lines.append(SubtitleLineData(text=label, text_secondary=""))

                flow_items.append(FlowItemData(
                    item_type=item.item_type,
                    label=label,
                    song_id=item.song_id,
                    lines=lines,
                ))

    # Initialize state in projection manager
    projection_manager._state[session.id] = ProjectionState(session_id=session.id)
    projection_manager.load_flow_data(session.id, session_in.flow_id, flow_items)

    return {"id": session.id, "flow_id": session.flow_id, "is_live": True}
