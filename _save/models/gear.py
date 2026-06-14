import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from strava_alt.database import Base


class Gear(Base):
    __tablename__ = "gear"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gear_type: Mapped[str] = mapped_column(String(50), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), default=None)
    model: Mapped[str | None] = mapped_column(String(255), default=None)
    nickname: Mapped[str | None] = mapped_column(String(255), default=None)
    distance_meters: Mapped[float] = mapped_column(Float, default=0.0)
    retired: Mapped[bool] = mapped_column(Boolean, default=False)
    retired_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    maintenance_interval_km: Mapped[float | None] = mapped_column(Float, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", back_populates="gear")
    activities = relationship("Activity", back_populates="gear")
