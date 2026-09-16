"""安全事件模型：聚合告警形成的处置单元。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class Incident(Base):
    """安全事件：可挂载多条告警与处置记录。"""

    __tablename__ = "soc_incidents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # 严重级别：critical / high / medium / low
    severity: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    # 状态机：open -> investigating -> contained -> closed
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    owner: Mapped[str] = mapped_column(String(128), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
