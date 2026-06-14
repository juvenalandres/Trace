from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class Lap(Base):
    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id"), nullable=False, index=True
    )
    lap_index: Mapped[int] = mapped_column(Integer, nullable=False)
    sport_type: Mapped[str | None] = mapped_column(String(50), default=None)
    distance_m: Mapped[float | None] = mapped_column(Float, default=None)
    duration_s: Mapped[float | None] = mapped_column(Float, default=None)
    avg_speed: Mapped[float | None] = mapped_column(Float, default=None)
    max_speed: Mapped[float | None] = mapped_column(Float, default=None)
    avg_hr: Mapped[float | None] = mapped_column(Float, default=None)
    max_hr: Mapped[int | None] = mapped_column(Integer, default=None)
    avg_power: Mapped[float | None] = mapped_column(Float, default=None)
    max_power: Mapped[int | None] = mapped_column(Integer, default=None)
    avg_cadence: Mapped[float | None] = mapped_column(Float, default=None)
    calories: Mapped[int | None] = mapped_column(Integer, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    activity: Mapped["Activity"] = relationship(back_populates="laps")  # noqa: F821
