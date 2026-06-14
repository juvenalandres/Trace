import datetime

from pydantic import BaseModel, ConfigDict, Field


class GearCreate(BaseModel):
    name: str = Field(max_length=255)
    gear_type: str = Field(max_length=50)
    brand: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=10000)
    maintenance_interval_km: float | None = None


class GearUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    gear_type: str | None = Field(default=None, max_length=50)
    brand: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=10000)
    retired: bool | None = None
    maintenance_interval_km: float | None = None
    last_service_date: datetime.date | None = None
    last_service_distance_m: float | None = None


class GearResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    gear_type: str
    brand: str | None = None
    model: str | None = None
    notes: str | None = None
    retired: bool
    retired_at: datetime.datetime | None = None
    maintenance_interval_km: float | None = None
    last_service_date: datetime.date | None = None
    last_service_distance_m: float | None = None
    created_at: datetime.datetime
