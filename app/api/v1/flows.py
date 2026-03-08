from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.worship_flow import FlowItem, WorshipFlow
from app.schemas.worship_flow import FlowCreate, FlowResponse

router = APIRouter()


@router.get("", response_model=list[FlowResponse])
async def list_flows(db: AsyncSession = Depends(get_db)):
    stmt = select(WorshipFlow).order_by(WorshipFlow.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=FlowResponse, status_code=201)
async def create_flow(flow_in: FlowCreate, db: AsyncSession = Depends(get_db)):
    items_data = flow_in.items
    flow = WorshipFlow(
        name=flow_in.name,
        date=flow_in.date,
        notes=flow_in.notes,
    )
    db.add(flow)
    await db.flush()

    for item_data in items_data:
        item = FlowItem(flow_id=flow.id, **item_data.model_dump())
        db.add(item)

    await db.flush()
    await db.refresh(flow, attribute_names=["items"])
    return flow


@router.get("/{flow_id}", response_model=FlowResponse)
async def get_flow(flow_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(WorshipFlow)
        .where(WorshipFlow.id == flow_id)
        .options(selectinload(WorshipFlow.items))
    )
    result = await db.execute(stmt)
    return result.scalar_one()


@router.delete("/{flow_id}", status_code=204)
async def delete_flow(flow_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(WorshipFlow).where(WorshipFlow.id == flow_id)
    result = await db.execute(stmt)
    flow = result.scalar_one()
    await db.delete(flow)
