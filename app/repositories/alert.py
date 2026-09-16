"""告警仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert


async def get_alert(session: AsyncSession, alert_id: str) -> Alert | None:
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    return result.scalar_one_or_none()


async def list_alerts(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    severity: str | None = None,
    status: str | None = None,
    incident_id: str | None = None,
    keyword: str | None = None,
) -> list[Alert]:
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit).offset(offset)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if status:
        stmt = stmt.where(Alert.status == status)
    if incident_id:
        stmt = stmt.where(Alert.incident_id == incident_id)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Alert.title.like(like), Alert.host.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_alerts(
    session: AsyncSession,
    severity: str | None = None,
    status: str | None = None,
    incident_id: str | None = None,
    keyword: str | None = None,
) -> int:
    stmt = select(func.count(Alert.id))
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if status:
        stmt = stmt.where(Alert.status == status)
    if incident_id:
        stmt = stmt.where(Alert.incident_id == incident_id)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Alert.title.like(like), Alert.host.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_alert(session: AsyncSession, alert: Alert) -> Alert:
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


async def update_alert(session: AsyncSession, alert: Alert) -> Alert:
    await session.commit()
    await session.refresh(alert)
    return alert
