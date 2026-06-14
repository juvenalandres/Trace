import datetime

from pydantic import BaseModel, ConfigDict, Field


class Waypoint(BaseModel):
    lat: float
    lng: float


class ElevationPoint(BaseModel):
    distance: float
    elevation: float


class RouteCreate(BaseModel):
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    waypoints: list[Waypoint]
    route_polyline: str | None = None
    distance_m: float = 0
    elevation_gain_m: float | None = None
    elevation_loss_m: float | None = None
    elevation_profile: list[ElevationPoint] | None = None
    sport_type: str | None = Field(default=None, max_length=50)


class RouteUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    waypoints: list[Waypoint] | None = None
    route_polyline: str | None = None
    distance_m: float | None = None
    elevation_gain_m: float | None = None
    elevation_loss_m: float | None = None
    elevation_profile: list[ElevationPoint] | None = None
    sport_type: str | None = Field(default=None, max_length=50)


class RouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str | None = None
    waypoints: list[Waypoint] = []
    route_polyline: str | None = None
    distance_m: float = 0
    elevation_gain_m: float | None = None
    elevation_loss_m: float | None = None
    elevation_profile: list[ElevationPoint] = []
    sport_type: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class RoutePlanRequest(BaseModel):
    waypoints: list[Waypoint]


class RoutePlanResponse(BaseModel):
    polyline: str
    distance_m: float
    waypoints: list[Waypoint]


class RouteElevationRequest(BaseModel):
    points: list[Waypoint]


class RouteElevationResponse(BaseModel):
    elevation_profile: list[ElevationPoint]
    elevation_gain_m: float
    elevation_loss_m: float
