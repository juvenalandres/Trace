import datetime

from pydantic import BaseModel, ConfigDict, Field


class ActivityStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    distance_m: float | None = None
    duration_s: float | None = None
    moving_time_s: float | None = None
    elevation_gain: float | None = None
    elevation_loss: float | None = None
    avg_speed: float | None = None
    max_speed: float | None = None
    avg_hr: float | None = None
    max_hr: int | None = None
    avg_power: float | None = None
    max_power: int | None = None
    normalized_power: float | None = None
    avg_cadence: float | None = None
    calories: int | None = None
    avg_temp: float | None = None
    polyline: str | None = None
    simplified_time_series: str | None = None
    elevation_profile: str | None = None
    min_lat: float | None = None
    max_lat: float | None = None
    min_lng: float | None = None
    max_lng: float | None = None


class LapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lap_index: int
    sport_type: str | None = None
    distance_m: float | None = None
    duration_s: float | None = None
    avg_speed: float | None = None
    max_speed: float | None = None
    avg_hr: float | None = None
    max_hr: int | None = None
    avg_power: float | None = None
    max_power: int | None = None
    avg_cadence: float | None = None
    calories: int | None = None
    notes: str | None = None


class ActivityCreate(BaseModel):
    name: str = Field(max_length=255)
    sport_type: str = Field(max_length=50)
    start_time: datetime.datetime
    timezone: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=10000)
    rpe: int | None = Field(default=None, ge=1, le=10)


class ActivityUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    sport_type: str | None = Field(default=None, max_length=50)
    timezone: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=10000)
    rpe: int | None = Field(default=None, ge=1, le=10)
    gear_id: int | None = None


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    sport_type: str
    start_time: datetime.datetime
    timezone: str | None = None
    source: str
    gear_id: int | None = None
    notes: str | None = None
    rpe: int | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    stats: ActivityStatsResponse | None = None
    laps: list[LapResponse] = []


class ActivitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sport_type: str
    start_time: datetime.datetime
    distance_m: float | None = None
    duration_s: float | None = None
    elevation_gain: float | None = None
    avg_speed: float | None = None
    avg_hr: float | None = None
    max_hr: int | None = None
    calories: int | None = None


class ActivityListResponse(BaseModel):
    items: list[ActivitySummary]
    total: int
    page: int
    page_size: int
