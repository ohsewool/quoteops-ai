"""Persisted guide state for explicit non-production V2 demo sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.demo import DemoRunStatus, demo_step_count
from backend.models.base import Base


class DemoRun(Base):
    __tablename__ = "demo_runs"
    __table_args__ = (
        CheckConstraint("current_step >= 0", name="ck_demo_runs_nonnegative_current_step"),
        CheckConstraint(
            f"current_step <= {demo_step_count()}",
            name="ck_demo_runs_current_step_in_range",
        ),
        CheckConstraint("version > 0", name="ck_demo_runs_positive_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[DemoRunStatus] = mapped_column(
        Enum(
            DemoRunStatus,
            name="demo_run_status",
            native_enum=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=DemoRunStatus.READY,
        index=True,
    )
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    artifacts_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
