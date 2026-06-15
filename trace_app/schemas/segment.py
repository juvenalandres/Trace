import datetime

from pydantic import BaseModel, ConfigDict, Field


class SegmentCreate(BaseModel):
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    sport_type: str | None = Field(default=None, max_length=50)
    start_lat: float = Field(ge=-90, le=90)
    start_lng: float = Field(ge=-180, le=180)
    end_lat: float = Field(ge=-90, le=90)
    end_lng: float = Field(ge=-180, le=180)
    polyline: str | None = None
    distance_m: float | None = None
    elevation_gain_m: float | None = None


class SegmentUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    sport_type: str | None = Field(default=None, max_length=50)


class SegmentEffortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    segment_id: int
    activity_id: int
    user_id: int
    user_name: str | None = None
    activity_name: str | None = None
    activity_start_time: datetime.datetime | None = None
    elapsed_time_s: float
    avg_speed: float | None = None
    avg_hr: float | None = None
    avg_power: float | None = None
    start_time: datetime.datetime
    created_at: datetime.datetime


class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    creator_name: str | None = None
    name: str
    description: str | None = None
    sport_type: str | None = None
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    polyline: str | None = None
    distance_m: float | None = None
    elevation_gain_m: float | None = None
    created_at: datetime.datetime
    best_time: float | None = None
    effort_count: int = 0


class SegmentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sport_type: str | None = None
    distance_m: float | None = None
    best_time: float | None = None
    effort_count: int = 0
    creator_name: str | None = None
    created_at: datetime.datetime


class SegmentPRResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    elapsed_time_s: float | None = None
    avg_speed: float | None = None
    avg_hr: float | None = None
    avg_power: float | None = None
    start_time: datetime.datetime | None = None
    activity_id: int | None = None


class SegmentLeaderboardEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    user_name: str | None = None
    elapsed_time_s: float
    avg_speed: float | None = None
    activity_id: int
    start_time: datetime.datetime
