"""安全事件服务层：状态机、告警聚合与处置流转。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.incident import Incident
from app.repositories import incident as repo
from app.repositories.incident import INCIDENT_TRANSITIONS
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.audit import record_audit


def _incident_to_dict(i: Incident) -> dict:
    return {
        "id": i.id, "title": i.title, "description": i.description,
        "severity": i.severity, "status": i.status, "owner": i.owner,
        "created_at": i.created_at.isoformat() if i.created_at else "",
        "updated_at": i.updated_at.isoformat() if i.updated_at else "",
    }


class IncidentService:
    @staticmethod
    async def list_incidents(
        session: AsyncSession, limit: int = 100, offset: int = 0,
        severity: str | None = None, status_filter: str | None = None,
        owner: str | None = None, keyword: str | None = None,
    ) -> dict:
        items = await repo.list_incidents(
            session, limit=limit, offset=offset, severity=severity,
            status=status_filter, owner=owner, keyword=keyword,
        )
        total = await repo.count_incidents(
            session, severity=severity, status=status_filter, owner=owner, keyword=keyword,
        )
        return {"total": total, "items": [_incident_to_dict(i) for i in items]}

    @staticmethod
    async def get_incident(session: AsyncSession, incident_id: str) -> dict:
        incident = await repo.get_incident(session, incident_id)
        if not incident:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "事件不存在")
        return _incident_to_dict(incident)

    @staticmethod
    async def create_incident(session: AsyncSession, payload: IncidentCreate,
                              request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        incident = Incident(
            id=str(uuid.uuid4()), title=payload.title, description=payload.description,
            severity=payload.severity, owner=payload.owner or "", status="open",
        )
        incident = await repo.create_incident(session, incident)
        await record_audit(session, "incident.created", "internal",
                           f"incident_id={incident.id} severity={payload.severity}", request)
        return _incident_to_dict(incident)

    @staticmethod
    async def update_incident(session: AsyncSession, incident_id: str, payload: IncidentUpdate,
                              request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        incident = await repo.get_incident(session, incident_id)
        if not incident:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "事件不存在")
        if payload.description is not None:
            incident.description = payload.description
        if payload.owner is not None:
            incident.owner = payload.owner
        incident = await repo.update_incident(session, incident)
        await record_audit(session, "incident.updated", "internal", f"incident_id={incident_id}", request)
        return _incident_to_dict(incident)

    @staticmethod
    async def change_status(session: AsyncSession, incident_id: str, new_status: str,
                            request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        incident = await repo.get_incident(session, incident_id)
        if not incident:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "事件不存在")
        allowed_next = INCIDENT_TRANSITIONS.get(incident.status, set())
        if new_status != incident.status and new_status not in allowed_next:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"非法状态迁移：{incident.status} -> {new_status}",
            )
        incident.status = new_status
        incident = await repo.update_incident(session, incident)
        await record_audit(session, "incident.status_changed", "internal",
                           f"incident_id={incident_id} status={new_status}", request)
        return _incident_to_dict(incident)
