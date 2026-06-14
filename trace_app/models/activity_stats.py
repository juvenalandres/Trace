from sqlalchemy import Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class ActivityStats(Base):
    __tablename__ = "activity_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id"), nullable=False, unique=True
    )
    distance_m: Mapped[float | None] = mapped_column(Float, default=None)
    duration_s: Mapped[float | None] = mapped_column(Float, default=None)
    moving_time_s: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_gain: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_loss: Mapped[float | None] = mapped_column(Float, default=None)
    avg_speed: Mapped[float | None] = mapped_column(Float, default=None)
    max_speed: Mapped[float | None] = mapped_column(Float, default=None)
    avg_hr: Mapped[float | None] = mapped_column(Float, default=None)
    max_hr: Mapped[int | None] = mapped_column(Integer, default=None)
    avg_power: Mapped[float | None] = mapped_column(Float, default=None)
    max_power: Mapped[int | None] = mapped_column(Integer, default=None)
    normalized_power: Mapped[float | None] = mapped_column(Float, default=None)
    avg_cadence: Mapped[float | None] = mapped_column(Float, default=None)
    calories: Mapped[int | None] = mapped_column(Integer, default=None)
    avg_temp: Mapped[float | None] = mapped_column(Float, default=None)
    polyline: Mapped[str | None] = mapped_column(Text, default=None)
    simplified_time_series: Mapped[str | None] = mapped_column(Text, default=None)
    elevation_profile: Mapped[str | None] = mapped_column(Text, default=None)
    min_lat: Mapped[float | None] = mapped_column(Float, default=None)
    max_lat: Mapped[float | None] = mapped_column(Float, default=None)
    min_lng: Mapped[float | None] = mapped_column(Float, default=None)
    max_lng: Mapped[float | None] = mapped_column(Float, default=None)
    training_load: Mapped[float | None] = mapped_column(Float, default=None)

    activity: Mapped["Activity"] = relationship(back_populates="stats")  # noqa: F821
