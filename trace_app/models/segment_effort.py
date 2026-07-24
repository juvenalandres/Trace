import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class SegmentEffort(Base):
    __tablename__ = "segment_efforts"
    __table_args__ = (
        UniqueConstraint("segment_id", "activity_id", "start_time", name="uq_segment_effort_activity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    segment_id: Mapped[int] = mapped_column(
        ForeignKey("segments.id"), nullable=False, index=True
    )
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    elapsed_time_s: Mapped[float] = mapped_column(Float, nullable=False)
    avg_speed: Mapped[float | None] = mapped_column(Float, default=None)
    avg_hr: Mapped[float | None] = mapped_column(Float, default=None)
    avg_power: Mapped[float | None] = mapped_column(Float, default=None)
    start_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    segment: Mapped["Segment"] = relationship(back_populates="efforts")  # noqa: F821
    activity: Mapped["Activity"] = relationship()  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="segment_efforts")  # noqa: F821
