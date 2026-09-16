"""处置记录服务层：事件响应动作流水。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.incident_response import IncidentResponse
from app.repositories import incident as incident_repo
from app.repositories import incident_response as repo
from app.schemas.incident_response import IncidentResponseCreate
from app.services.audit import record_audit

# 处置状态机：pending 可转 completed / failed
RESPONSE_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"completed", "failed"},
    "completed": set(),
    "failed": {"pending"},
}


def _resp_to_dict(r: IncidentResponse) -> dict:
    return {
        "id": r.id, "incident_id": r.incident_id, "action": r.action,
        "operator": r.operator, "status": r.status, "note": r.note,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


class ResponseService:
    @staticmethod
    async def list_responses(session: AsyncSession, incident_id: str,
                             limit: int = 100, offset: int = 0,
                             status_filter: str | None = None) -> dict:
        items = await repo.list_responses(
            session, incident_id, limit=limit, offset=offset, status=status_filter,
        )
        total = await repo.count_responses(session, incident_id, status=status_filter)
        return {"total": total, "items": [_resp_to_dict(r) for r in items]}

    @staticmethod
    async def get_response(session: AsyncSession, response_id: str) -> dict:
        response = await repo.get_response(session, response_id)
        if not response:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "处置记录不存在")
        return _resp_to_dict(response)

    @staticmethod
    async def create_response(session: AsyncSession, incident_id: str,
                              payload: IncidentResponseCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        incident = await incident_repo.get_incident(session, incident_id)
        if not incident:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "事件不存在")
        response = IncidentResponse(
            id=str(uuid.uuid4()), incident_id=incident_id, action=payload.action,
            operator=payload.operator or "", status="pending", note=payload.note,
        )
        response = await repo.create_response(session, response)
        await record_audit(session, "response.created", "internal",
                           f"response_id={response.id} incident_id={incident_id}", request)
        return _resp_to_dict(response)

    @staticmethod
    async def change_status(session: AsyncSession, response_id: str, new_status: str,
                            request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        response = await repo.get_response(session, response_id)
        if not response:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "处置记录不存在")
        allowed_next = RESPONSE_TRANSITIONS.get(response.status, set())
        if new_status != response.status and new_status not in allowed_next:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"非法处置状态迁移：{response.status} -> {new_status}",
            )
        response.status = new_status
        response = await repo.update_response(session, response)
        await record_audit(session, "response.status_changed", "internal",
                           f"response_id={response_id} status={new_status}", request)
        return _resp_to_dict(response)
