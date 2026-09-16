"""告警服务层：严重级别、状态流转与事件关联。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.alert import Alert
from app.repositories import alert as repo
from app.repositories import incident as incident_repo
from app.schemas.alert import AlertCreate
from app.services.audit import record_audit


def _alert_to_dict(a: Alert) -> dict:
    return {
        "id": a.id, "source": a.source, "title": a.title, "description": a.description,
        "severity": a.severity, "status": a.status, "host": a.host,
        "incident_id": a.incident_id,
        "created_at": a.created_at.isoformat() if a.created_at else "",
    }


class AlertService:
    @staticmethod
    async def list_alerts(
        session: AsyncSession, limit: int = 100, offset: int = 0,
        severity: str | None = None, status_filter: str | None = None,
        incident_id: str | None = None, keyword: str | None = None,
    ) -> dict:
        items = await repo.list_alerts(
            session, limit=limit, offset=offset, severity=severity,
            status=status_filter, incident_id=incident_id, keyword=keyword,
        )
        total = await repo.count_alerts(
            session, severity=severity, status=status_filter,
            incident_id=incident_id, keyword=keyword,
        )
        return {"total": total, "items": [_alert_to_dict(a) for a in items]}

    @staticmethod
    async def get_alert(session: AsyncSession, alert_id: str) -> dict:
        alert = await repo.get_alert(session, alert_id)
        if not alert:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "告警不存在")
        return _alert_to_dict(alert)

    @staticmethod
    async def create_alert(session: AsyncSession, payload: AlertCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        alert = Alert(
            id=str(uuid.uuid4()), source=payload.source, title=payload.title,
            description=payload.description, severity=payload.severity,
            host=payload.host, status="active",
        )
        alert = await repo.create_alert(session, alert)
        await record_audit(session, "alert.created", "internal",
                           f"alert_id={alert.id} severity={payload.severity}", request)
        return _alert_to_dict(alert)

    @staticmethod
    async def change_status(session: AsyncSession, alert_id: str, new_status: str,
                            request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        alert = await repo.get_alert(session, alert_id)
        if not alert:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "告警不存在")
        alert.status = new_status
        alert = await repo.update_alert(session, alert)
        await record_audit(session, "alert.status_changed", "internal",
                           f"alert_id={alert_id} status={new_status}", request)
        return _alert_to_dict(alert)

    @staticmethod
    async def associate_incident(session: AsyncSession, alert_id: str, incident_id: str,
                                 request: Request) -> dict:
        """将告警关联到既有安全事件。"""
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        alert = await repo.get_alert(session, alert_id)
        if not alert:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "告警不存在")
        incident = await incident_repo.get_incident(session, incident_id)
        if not incident:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "关联事件不存在")
        alert.incident_id = incident_id
        # 关联后告警自动转为已确认
        alert.status = "acknowledged"
        alert = await repo.update_alert(session, alert)
        await record_audit(session, "alert.associated", "internal",
                           f"alert_id={alert_id} incident_id={incident_id}", request)
        return _alert_to_dict(alert)
