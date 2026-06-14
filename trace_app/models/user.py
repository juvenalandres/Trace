import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from trace_app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), default=None)
    name: Mapped[str | None] = mapped_column(String(255), default=None)
    preferred_units: Mapped[str] = mapped_column(String(20), default="metric")
    weight_kg: Mapped[float | None] = mapped_column(default=None)
    ftp_watts: Mapped[int | None] = mapped_column(Integer, default=None)
    max_hr: Mapped[int | None] = mapped_column(Integer, default=None)
    resting_hr: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    activities: Mapped[list["Activity"]] = relationship(back_populates="user")  # noqa: F821
    gear: Mapped[list["Gear"]] = relationship(back_populates="user")  # noqa: F821
    sync_sources: Mapped[list["SyncSource"]] = relationship(back_populates="user")  # noqa: F821
    zones: Mapped[list["UserZone"]] = relationship(back_populates="user")  # noqa: F821
    training_plans: Mapped[list["TrainingPlan"]] = relationship(back_populates="user")  # noqa: F821
    daily_training_loads: Mapped[list["DailyTrainingLoad"]] = relationship(back_populates="user")  # noqa: F821
    routes: Mapped[list["Route"]] = relationship(back_populates="user")  # noqa: F821
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")  # noqa: F821
