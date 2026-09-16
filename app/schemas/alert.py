"""告警 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low"]


class AlertCreate(BaseModel):
    source: str = Field(default="", max_length=64)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    severity: Severity = "medium"
    host: str = Field(default="", max_length=128)


class AlertStatusUpdate(BaseModel):
    status: Literal["active", "acknowledged", "resolved", "false_positive"]


class AlertAssociate(BaseModel):
    incident_id: str = Field(min_length=1, max_length=64)


class AlertResponse(BaseModel):
    id: str
    source: str
    title: str
    description: str
    severity: str
    status: str
    host: str
    incident_id: str
    created_at: datetime


class AlertListResponse(BaseModel):
    total: int
    items: list[AlertResponse]
