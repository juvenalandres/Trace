import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class UserZone(Base):
    __tablename__ = "user_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    zone_type: Mapped[str] = mapped_column(String(50), nullable=False)
    zone_1_min: Mapped[float | None] = mapped_column(Float, default=None)
    zone_1_max: Mapped[float | None] = mapped_column(Float, default=None)
    zone_2_min: Mapped[float | None] = mapped_column(Float, default=None)
    zone_2_max: Mapped[float | None] = mapped_column(Float, default=None)
    zone_3_min: Mapped[float | None] = mapped_column(Float, default=None)
    zone_3_max: Mapped[float | None] = mapped_column(Float, default=None)
    zone_4_min: Mapped[float | None] = mapped_column(Float, default=None)
    zone_4_max: Mapped[float | None] = mapped_column(Float, default=None)
    zone_5_min: Mapped[float | None] = mapped_column(Float, default=None)
    zone_5_max: Mapped[float | None] = mapped_column(Float, default=None)
    valid_from: Mapped[datetime.date | None] = mapped_column(default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="zones")  # noqa: F821
