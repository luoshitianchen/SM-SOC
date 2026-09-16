"""事件处置记录路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.incident_response import IncidentResponseCreate, IncidentResponseStatusUpdate
from app.services.incident_response import ResponseService

router = APIRouter(prefix="/api/soc", tags=["soc-responses"])


@router.get("/incidents/{incident_id}/responses")
async def list_responses(
    incident_id: str, request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ResponseService.list_responses(
        session, incident_id, limit=limit, offset=offset, status_filter=status_filter,
    )


@router.post("/incidents/{incident_id}/responses", status_code=status.HTTP_201_CREATED)
async def create_response(
    incident_id: str, payload: IncidentResponseCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ResponseService.create_response(session, incident_id, payload, request)


@router.get("/responses/{response_id}")
async def get_response(
    response_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ResponseService.get_response(session, response_id)


@router.patch("/responses/{response_id}/status")
async def change_status(
    response_id: str, payload: IncidentResponseStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ResponseService.change_status(session, response_id, payload.status, request)
