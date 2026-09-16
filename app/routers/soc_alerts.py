"""告警管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.alert import AlertAssociate, AlertCreate, AlertStatusUpdate
from app.services.alert import AlertService

router = APIRouter(prefix="/api/soc/alerts", tags=["soc-alerts"])


@router.get("")
async def list_alerts(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    incident_id: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AlertService.list_alerts(
        session, limit=limit, offset=offset, severity=severity,
        status_filter=status_filter, incident_id=incident_id, keyword=keyword,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: AlertCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AlertService.create_alert(session, payload, request)


@router.get("/{alert_id}")
async def get_alert(
    alert_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AlertService.get_alert(session, alert_id)


@router.patch("/{alert_id}/status")
async def change_status(
    alert_id: str, payload: AlertStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AlertService.change_status(session, alert_id, payload.status, request)


@router.post("/{alert_id}/associate")
async def associate(
    alert_id: str, payload: AlertAssociate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AlertService.associate_incident(session, alert_id, payload.incident_id, request)
