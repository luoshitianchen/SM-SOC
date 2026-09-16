"""处置记录仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident_response import IncidentResponse


async def get_response(session: AsyncSession, response_id: str) -> IncidentResponse | None:
    result = await session.execute(select(IncidentResponse).where(IncidentResponse.id == response_id))
    return result.scalar_one_or_none()


async def list_responses(
    session: AsyncSession,
    incident_id: str,
    limit: int = 100,
    offset: int = 0,
    status: str | None = None,
) -> list[IncidentResponse]:
    stmt = (
        select(IncidentResponse)
        .where(IncidentResponse.incident_id == incident_id)
        .order_by(IncidentResponse.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        stmt = stmt.where(IncidentResponse.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_responses(session: AsyncSession, incident_id: str,
                          status: str | None = None) -> int:
    stmt = select(func.count(IncidentResponse.id)).where(
        IncidentResponse.incident_id == incident_id
    )
    if status:
        stmt = stmt.where(IncidentResponse.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_response(session: AsyncSession, response: IncidentResponse) -> IncidentResponse:
    session.add(response)
    await session.commit()
    await session.refresh(response)
    return response


async def update_response(session: AsyncSession, response: IncidentResponse) -> IncidentResponse:
    await session.commit()
    await session.refresh(response)
    return response
