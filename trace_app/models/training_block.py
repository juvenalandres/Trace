import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class TrainingBlock(Base):
    __tablename__ = "training_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("training_plans.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    focus: Mapped[str | None] = mapped_column(String(100), default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[datetime.date | None] = mapped_column(Date, default=None)
    end_date: Mapped[datetime.date | None] = mapped_column(Date, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    plan: Mapped["TrainingPlan"] = relationship(back_populates="blocks")  # noqa: F821
    sessions: Mapped[list["TrainingSession"]] = relationship(  # noqa: F821
        back_populates="block"
    )
