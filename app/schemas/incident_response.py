"""处置记录 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IncidentResponseCreate(BaseModel):
    action: str = Field(min_length=1, max_length=200)
    operator: str = Field(default="", max_length=128)
    note: str = Field(default="", max_length=2000)


class IncidentResponseStatusUpdate(BaseModel):
    status: Literal["pending", "completed", "failed"]


class IncidentResponseItem(BaseModel):
    id: str
    incident_id: str
    action: str
    operator: str
    status: str
    note: str
    created_at: datetime


class IncidentResponseList(BaseModel):
    total: int
    items: list[IncidentResponseItem]
