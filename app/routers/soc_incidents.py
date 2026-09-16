"""安全事件管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.incident import IncidentCreate, IncidentStatusUpdate, IncidentUpdate
from app.services.incident import IncidentService

router = APIRouter(prefix="/api/soc/incidents", tags=["soc-incidents"])


@router.get("")
async def list_incidents(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    owner: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await IncidentService.list_incidents(
        session, limit=limit, offset=offset, severity=severity,
        status_filter=status_filter, owner=owner, keyword=keyword,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await IncidentService.create_incident(session, payload, request)


@router.get("/{incident_id}")
async def get_incident(
    incident_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await IncidentService.get_incident(session, incident_id)


@router.patch("/{incident_id}")
async def update_incident(
    incident_id: str, payload: IncidentUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await IncidentService.update_incident(session, incident_id, payload, request)


@router.patch("/{incident_id}/status")
async def change_status(
    incident_id: str, payload: IncidentStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await IncidentService.change_status(session, incident_id, payload.status, request)
