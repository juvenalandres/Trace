import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    sport_type: Mapped[str | None] = mapped_column(String(50), default=None)
    start_lat: Mapped[float] = mapped_column(Float, nullable=False)
    start_lng: Mapped[float] = mapped_column(Float, nullable=False)
    end_lat: Mapped[float] = mapped_column(Float, nullable=False)
    end_lng: Mapped[float] = mapped_column(Float, nullable=False)
    polyline: Mapped[str | None] = mapped_column(Text, default=None)
    distance_m: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="segments")  # noqa: F821
    efforts: Mapped[list["SegmentEffort"]] = relationship(  # noqa: F821
        back_populates="segment", cascade="all, delete-orphan"
    )
