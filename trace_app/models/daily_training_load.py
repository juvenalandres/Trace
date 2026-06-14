import datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class DailyTrainingLoad(Base):
    __tablename__ = "daily_training_load"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    training_load: Mapped[float] = mapped_column(Float, default=0.0)
    ctl: Mapped[float] = mapped_column(Float, default=0.0)
    atl: Mapped[float] = mapped_column(Float, default=0.0)
    tsb: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="daily_training_loads")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_date_training_load"),
    )
