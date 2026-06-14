import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from strava_alt.database import Base


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    sport_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    timezone: Mapped[str | None] = mapped_column(String(50), default=None)
    distance_meters: Mapped[float | None] = mapped_column(Float, default=None)
    duration_seconds: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_gain_meters: Mapped[float | None] = mapped_column(Float, default=None)
    avg_speed: Mapped[float | None] = mapped_column(Float, default=None)
    max_speed: Mapped[float | None] = mapped_column(Float, default=None)
    avg_heartrate: Mapped[float | None] = mapped_column(Float, default=None)
    max_heartrate: Mapped[float | None] = mapped_column(Float, default=None)
    calories: Mapped[int | None] = mapped_column(Integer, default=None)
    perceived_exertion: Mapped[int | None] = mapped_column(Integer, default=None)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    gear_id: Mapped[int | None] = mapped_column(ForeignKey("gear.id"), default=None)
    training_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("training_plans.id"), default=None
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="activities")
    gear = relationship("Gear", back_populates="activities")
    training_plan = relationship("TrainingPlan", back_populates="activity")
    segment_efforts = relationship("SegmentEffort", back_populates="activity")
