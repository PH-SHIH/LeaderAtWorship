from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.worship_flow import FlowItem, WorshipFlow
from app.schemas.worship_flow import (
    FlowCreate,
    FlowItemResponse,
    FlowResponse,
    FlowUpdate,
)

router = APIRouter()


def _enrich_flow_response(flow: WorshipFlow) -> FlowResponse:
    """Convert ORM flow to response with song_title on each item."""
    items = []
    for item in flow.items:
        resp = FlowItemResponse.model_validate(item)
        if item.song:
            resp.song_title = item.song.title
        items.append(resp)
    return FlowResponse(
        id=flow.id,
        name=flow.name,
        date=flow.date,
        notes=flow.notes,
        created_at=flow.created_at,
        items=items,
    )


def _flow_query():
    return (
        select(WorshipFlow)
        .options(
            selectinload(WorshipFlow.items).selectinload(FlowItem.song)
        )
    )


@router.get("", response_model=list[FlowResponse])
async def list_flows(db: AsyncSession = Depends(get_db)):
    stmt = _flow_query().order_by(WorshipFlow.created_at.desc())
    result = await db.execute(stmt)
    return [_enrich_flow_response(f) for f in result.scalars().all()]


@router.post("", response_model=FlowResponse, status_code=201)
async def create_flow(flow_in: FlowCreate, db: AsyncSession = Depends(get_db)):
    flow = WorshipFlow(
        name=flow_in.name,
        date=flow_in.date,
        notes=flow_in.notes,
    )
    db.add(flow)
    await db.flush()

    for item_data in flow_in.items:
        item = FlowItem(flow_id=flow.id, **item_data.model_dump())
        db.add(item)

    await db.flush()

    # Re-query with joins for enriched response
    stmt = _flow_query().where(WorshipFlow.id == flow.id)
    result = await db.execute(stmt)
    return _enrich_flow_response(result.scalar_one())


@router.get("/{flow_id}", response_model=FlowResponse)
async def get_flow(flow_id: int, db: AsyncSession = Depends(get_db)):
    stmt = _flow_query().where(WorshipFlow.id == flow_id)
    result = await db.execute(stmt)
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return _enrich_flow_response(flow)


@router.put("/{flow_id}", response_model=FlowResponse)
async def update_flow(
    flow_id: int, flow_in: FlowUpdate, db: AsyncSession = Depends(get_db)
):
    stmt = _flow_query().where(WorshipFlow.id == flow_id)
    result = await db.execute(stmt)
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    # Update basic fields
    if flow_in.name is not None:
        flow.name = flow_in.name
    if flow_in.date is not None:
        flow.date = flow_in.date
    if flow_in.notes is not None:
        flow.notes = flow_in.notes

    # Replace items if provided
    if flow_in.items is not None:
        await db.execute(
            delete(FlowItem).where(FlowItem.flow_id == flow_id)
        )
        for item_data in flow_in.items:
            item = FlowItem(flow_id=flow_id, **item_data.model_dump())
            db.add(item)
        await db.flush()

    # Re-query for enriched response
    stmt = _flow_query().where(WorshipFlow.id == flow_id)
    result = await db.execute(stmt)
    return _enrich_flow_response(result.scalar_one())


@router.delete("/{flow_id}", status_code=204)
async def delete_flow(flow_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(WorshipFlow).where(WorshipFlow.id == flow_id)
    result = await db.execute(stmt)
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    await db.delete(flow)
