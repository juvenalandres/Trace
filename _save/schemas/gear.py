import datetime

from pydantic import BaseModel, ConfigDict


class GearCreate(BaseModel):
    name: str
    gear_type: str
    brand: str | None = None
    model: str | None = None
    nickname: str | None = None
    maintenance_interval_km: float | None = None


class GearUpdate(BaseModel):
    name: str | None = None
    gear_type: str | None = None
    brand: str | None = None
    model: str | None = None
    nickname: str | None = None
    distance_meters: float | None = None
    retired: bool | None = None
    maintenance_interval_km: float | None = None


class GearResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    gear_type: str
    brand: str | None = None
    model: str | None = None
    nickname: str | None = None
    distance_meters: float
    retired: bool
    retired_at: datetime.datetime | None = None
    maintenance_interval_km: float | None = None
    created_at: datetime.datetime
