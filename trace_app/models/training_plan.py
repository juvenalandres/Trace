import datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    start_date: Mapped[datetime.date | None] = mapped_column(Date, default=None)
    end_date: Mapped[datetime.date | None] = mapped_column(Date, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="training_plans")  # noqa: F821
    sessions: Mapped[list["TrainingSession"]] = relationship(  # noqa: F821
        back_populates="plan", cascade="all, delete-orphan"
    )
