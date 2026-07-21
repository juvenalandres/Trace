import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base
from trace_app.models.enums import Source, SportType


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sport_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    timezone: Mapped[str | None] = mapped_column(String(50), default=None)
    source: Mapped[str] = mapped_column(String(50), default=Source.MANUAL.value)
    raw_file_path: Mapped[str | None] = mapped_column(String(500), default=None)
    file_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    gear_id: Mapped[int | None] = mapped_column(ForeignKey("gear.id"), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    rpe: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="activities")  # noqa: F821
    stats: Mapped["ActivityStats | None"] = relationship(  # noqa: F821
        back_populates="activity", uselist=False, cascade="all, delete-orphan"
    )
    laps: Mapped[list["Lap"]] = relationship(  # noqa: F821
        back_populates="activity", cascade="all, delete-orphan"
    )
