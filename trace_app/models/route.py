import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    waypoints: Mapped[list | None] = mapped_column(JSON, default=None)
    route_polyline: Mapped[str | None] = mapped_column(Text, default=None)
    distance_m: Mapped[float] = mapped_column(Float, default=0)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_loss_m: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_profile: Mapped[list | None] = mapped_column(JSON, default=None)
    sport_type: Mapped[str | None] = mapped_column(String(50), default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="routes")  # noqa: F821
