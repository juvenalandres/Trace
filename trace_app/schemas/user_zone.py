import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserZoneCreate(BaseModel):
    zone_type: str = Field(max_length=20)
    zone_1_min: float | None = None
    zone_1_max: float | None = None
    zone_2_min: float | None = None
    zone_2_max: float | None = None
    zone_3_min: float | None = None
    zone_3_max: float | None = None
    zone_4_min: float | None = None
    zone_4_max: float | None = None
    zone_5_min: float | None = None
    zone_5_max: float | None = None
    valid_from: datetime.date | None = None


class UserZoneUpdate(BaseModel):
    zone_1_min: float | None = None
    zone_1_max: float | None = None
    zone_2_min: float | None = None
    zone_2_max: float | None = None
    zone_3_min: float | None = None
    zone_3_max: float | None = None
    zone_4_min: float | None = None
    zone_4_max: float | None = None
    zone_5_min: float | None = None
    zone_5_max: float | None = None


class UserZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    zone_type: str
    zone_1_min: float | None = None
    zone_1_max: float | None = None
    zone_2_min: float | None = None
    zone_2_max: float | None = None
    zone_3_min: float | None = None
    zone_3_max: float | None = None
    zone_4_min: float | None = None
    zone_4_max: float | None = None
    zone_5_min: float | None = None
    zone_5_max: float | None = None
    valid_from: datetime.date | None = None
    created_at: datetime.datetime
