import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class Gear(Base):
    __tablename__ = "gear"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gear_type: Mapped[str] = mapped_column(String(50), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), default=None)
    model: Mapped[str | None] = mapped_column(String(255), default=None)
    notes: Mapped[str | None] = mapped_column(String(1000), default=None)
    retired: Mapped[bool] = mapped_column(Boolean, default=False)
    retired_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    maintenance_interval_km: Mapped[float | None] = mapped_column(Float, default=None)
    last_service_date: Mapped[datetime.date | None] = mapped_column(default=None)
    last_service_distance_m: Mapped[float | None] = mapped_column(Float, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="gear")  # noqa: F821
