"""SM SOC —— 安全运营中心：告警接入、事件研判、安全剧本与工单闭环。"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from app import base

SERVICE = "sm-soc"
VERSION = "3.0.0"
NAME = "SM SOC"
DESCRIPTION = "安全运营中心：告警接入、事件研判、安全剧本与工单闭环"
PORT = 8460


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _init() -> None:
    with base.db_ctx() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, severity TEXT NOT NULL,
                source TEXT NOT NULL, description TEXT, status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL, resolved_at TEXT
            );
            CREATE TABLE IF NOT EXISTS playbooks (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, steps TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open', alert_count INTEGER NOT NULL DEFAULT 0,
                playbook_id TEXT, created_at TEXT NOT NULL, resolved_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity, status);
            """
        )


app = base.create_app(
    service=SERVICE, name=NAME, description=DESCRIPTION, version=VERSION, port=PORT,
    dependencies=["sm-iam", "sm-event-bus", "sm-audit-log-center"],
    events=["alert.ingested", "incident.created", "incident.resolved"],
    overview_fn=lambda _r: {
        "summary": {
            "open_alerts": base.get_db().execute("SELECT COUNT(*) FROM alerts WHERE status='open'").fetchone()[0],
            "open_incidents": base.get_db().execute("SELECT COUNT(*) FROM incidents WHERE status<>'resolved'").fetchone()[0],
        }
    },
)
_init()


class AlertIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    severity: str = Field(pattern=r"^(critical|high|medium|low)$")
    source: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000)


class PlaybookIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    steps: list[str] = Field(min_length=1)


class IncidentIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    severity: str = Field(pattern=r"^(critical|high|medium|low)$")
    alert_ids: list[str] = Field(default_factory=list)
    playbook_id: str | None = Field(default=None, max_length=64)


@app.post("/api/soc/alerts", status_code=status.HTTP_201_CREATED)
def ingest_alert(payload: AlertIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    alert_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        conn.execute("INSERT INTO alerts (id, title, severity, source, description, status, created_at) VALUES (?,?,?,?,?,?,?)", (alert_id, payload.title, payload.severity, payload.source, payload.description, "open", _now()))
        base.record_audit("alert.ingested", "internal", f"alert={alert_id} severity={payload.severity}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": alert_id, "severity": payload.severity, "status": "open"}


@app.get("/api/soc/alerts")
def list_alerts(severity: str | None = None, status_: str | None = None) -> dict[str, Any]:
    clauses, params = [], []
    if severity:
        clauses.append("severity=?")
        params.append(severity)
    if status_:
        clauses.append("status=?")
        params.append(status_)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with base.db_ctx() as conn:
        rows = conn.execute(f"SELECT * FROM alerts{where} ORDER BY created_at DESC LIMIT 200", params).fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/soc/alerts/{alert_id}/ack")
def acknowledge_alert(alert_id: str, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    return _set_alert(alert_id, "acknowledged", request)


@app.post("/api/soc/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    return _set_alert(alert_id, "resolved", request)


def _set_alert(alert_id: str, status_: str, request: Request) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if conn.execute("UPDATE alerts SET status=?, resolved_at=CASE WHEN ?='resolved' THEN ? ELSE resolved_at END WHERE id=?", (status_, status_, _now(), alert_id)).rowcount == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "告警不存在")
    return {"id": alert_id, "status": status_}


@app.post("/api/soc/playbooks", status_code=status.HTTP_201_CREATED)
def create_playbook(payload: PlaybookIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    playbook_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        try:
            conn.execute("INSERT INTO playbooks VALUES (?,?,?,?)", (playbook_id, payload.name, json.dumps(payload.steps, ensure_ascii=False), _now()))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "剧本已存在") from exc
    return {"id": playbook_id, "name": payload.name}


@app.get("/api/soc/playbooks")
def list_playbooks() -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM playbooks ORDER BY created_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/soc/incidents", status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    incident_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        if payload.playbook_id and not conn.execute("SELECT 1 FROM playbooks WHERE id=?", (payload.playbook_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "剧本不存在")
        for alert_id in payload.alert_ids:
            conn.execute("UPDATE alerts SET status='acknowledged' WHERE id=?", (alert_id,))
        conn.execute("INSERT INTO incidents (id, title, severity, status, alert_count, playbook_id, created_at) VALUES (?,?,?,?,?,?,?)", (incident_id, payload.title, payload.severity, "open", len(payload.alert_ids), payload.playbook_id, _now()))
        base.record_audit("incident.created", "internal", f"incident={incident_id} severity={payload.severity}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": incident_id, "title": payload.title, "status": "open"}


@app.get("/api/soc/incidents")
def list_incidents(status_: str | None = None) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if status_:
            rows = conn.execute("SELECT * FROM incidents WHERE status=? ORDER BY created_at DESC", (status_,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM incidents ORDER BY created_at DESC LIMIT 200").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/soc/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    with base.db_ctx() as conn:
        if conn.execute("UPDATE incidents SET status='resolved', resolved_at=? WHERE id=?", (_now(), incident_id)).rowcount == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "安全事件不存在")
        base.record_audit("incident.resolved", "internal", f"incident={incident_id}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": incident_id, "status": "resolved"}


@app.get("/api/soc/stats")
def stats() -> dict[str, Any]:
    with base.db_ctx() as conn:
        def _count(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]
        return {
            "alerts_open": _count("SELECT COUNT(*) FROM alerts WHERE status='open'"),
            "alerts_acknowledged": _count("SELECT COUNT(*) FROM alerts WHERE status='acknowledged'"),
            "alerts_resolved": _count("SELECT COUNT(*) FROM alerts WHERE status='resolved'"),
            "incidents_open": _count("SELECT COUNT(*) FROM incidents WHERE status<>'resolved'"),
            "critical": _count("SELECT COUNT(*) FROM alerts WHERE severity='critical' AND status<>'resolved'"),
            "high": _count("SELECT COUNT(*) FROM alerts WHERE severity='high' AND status<>'resolved'"),
        }