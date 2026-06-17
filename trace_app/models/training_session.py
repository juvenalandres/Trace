import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("training_plans.id"), nullable=False, index=True
    )
    scheduled_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    sport_type: Mapped[str | None] = mapped_column(String(50), default=None)
    name: Mapped[str | None] = mapped_column(String(255), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    targets: Mapped[list | None] = mapped_column(JSON, default=None)
    intervals: Mapped[str | None] = mapped_column(Text, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    rest_day: Mapped[bool] = mapped_column(Boolean, default=False)
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id"), default=None
    )
    block_id: Mapped[int | None] = mapped_column(
        ForeignKey("training_blocks.id", ondelete="SET NULL"), default=None
    )
    status: Mapped[str] = mapped_column(String(50), default="planned")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    plan: Mapped["TrainingPlan"] = relationship(back_populates="sessions")  # noqa: F821
    block: Mapped["TrainingBlock | None"] = relationship(  # noqa: F821
        back_populates="sessions"
    )
