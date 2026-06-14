from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from strava_alt.database import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id"), nullable=False, unique=True
    )
    polyline: Mapped[str | None] = mapped_column(Text, default=None)
    elevation_profile: Mapped[str | None] = mapped_column(Text, default=None)
    min_lat: Mapped[float | None] = mapped_column(Float, default=None)
    max_lat: Mapped[float | None] = mapped_column(Float, default=None)
    min_lng: Mapped[float | None] = mapped_column(Float, default=None)
    max_lng: Mapped[float | None] = mapped_column(Float, default=None)
    time_series: Mapped[str | None] = mapped_column(Text, default=None)
