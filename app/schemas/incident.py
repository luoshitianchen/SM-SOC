"""安全事件 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.alert import Severity


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    severity: Severity = "medium"
    owner: str = Field(default="", max_length=128)


class IncidentUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=4000)
    owner: str | None = Field(default=None, max_length=128)


class IncidentStatusUpdate(BaseModel):
    status: Literal["open", "investigating", "contained", "closed"]


class IncidentResponse(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    status: str
    owner: str
    created_at: datetime
    updated_at: datetime


class IncidentListResponse(BaseModel):
    total: int
    items: list[IncidentResponse]
