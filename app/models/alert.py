"""告警模型：SOC 原始安全告警。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class Alert(Base):
    """告警：由检测引擎上报的安全信号。"""

    __tablename__ = "soc_alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(64), default="", index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # 严重级别：critical / high / medium / low
    severity: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    # 状态：active / acknowledged / resolved / false_positive
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    host: Mapped[str] = mapped_column(String(128), default="")
    # 关联的安全事件，未关联时为空
    incident_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
