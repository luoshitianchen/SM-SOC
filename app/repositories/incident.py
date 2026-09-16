"""安全事件仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident

# 事件状态机：合法的前置->后置迁移
INCIDENT_TRANSITIONS: dict[str, set[str]] = {
    "open": {"investigating"},
    "investigating": {"contained"},
    "contained": {"closed"},
    "closed": set(),
}


async def get_incident(session: AsyncSession, incident_id: str) -> Incident | None:
    result = await session.execute(select(Incident).where(Incident.id == incident_id))
    return result.scalar_one_or_none()


async def list_incidents(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    severity: str | None = None,
    status: str | None = None,
    owner: str | None = None,
    keyword: str | None = None,
) -> list[Incident]:
    stmt = select(Incident).order_by(Incident.created_at.desc()).limit(limit).offset(offset)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if status:
        stmt = stmt.where(Incident.status == status)
    if owner:
        stmt = stmt.where(Incident.owner == owner)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(Incident.title.like(like))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_incidents(
    session: AsyncSession,
    severity: str | None = None,
    status: str | None = None,
    owner: str | None = None,
    keyword: str | None = None,
) -> int:
    stmt = select(func.count(Incident.id))
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if status:
        stmt = stmt.where(Incident.status == status)
    if owner:
        stmt = stmt.where(Incident.owner == owner)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(Incident.title.like(like))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_incident(session: AsyncSession, incident: Incident) -> Incident:
    session.add(incident)
    await session.commit()
    await session.refresh(incident)
    return incident


async def update_incident(session: AsyncSession, incident: Incident) -> Incident:
    await session.commit()
    await session.refresh(incident)
    return incident
