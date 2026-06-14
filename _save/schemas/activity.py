import datetime

from pydantic import BaseModel, ConfigDict, Field


class ActivityCreate(BaseModel):
    name: str
    description: str | None = None
    sport_type: str
    start_time: datetime.datetime
    timezone: str | None = None
    distance_meters: float | None = None
    duration_seconds: float | None = None
    elevation_gain_meters: float | None = None
    avg_heartrate: float | None = None
    max_heartrate: float | None = None
    calories: int | None = None
    perceived_exertion: int | None = None
    gear_id: int | None = None


class ActivityUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sport_type: str | None = None
    timezone: str | None = None
    distance_meters: float | None = None
    duration_seconds: float | None = None
    elevation_gain_meters: float | None = None
    avg_heartrate: float | None = None
    max_heartrate: float | None = None
    calories: int | None = None
    perceived_exertion: int | None = None
    gear_id: int | None = None


class RouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    polyline: str | None = None
    elevation_profile: str | None = None
    time_series: str | None = None
    min_lat: float | None = None
    max_lat: float | None = None
    min_lng: float | None = None
    max_lng: float | None = None


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str | None = None
    sport_type: str
    start_time: datetime.datetime
    timezone: str | None = None
    distance_meters: float | None = None
    duration_seconds: float | None = None
    elevation_gain_meters: float | None = None
    avg_speed: float | None = None
    max_speed: float | None = None
    avg_heartrate: float | None = None
    max_heartrate: float | None = None
    calories: int | None = None
    perceived_exertion: int | None = None
    source: str
    gear_id: int | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    route: RouteResponse | None = None


class ActivitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sport_type: str
    start_time: datetime.datetime
    distance_meters: float | None = None
    duration_seconds: float | None = None
    elevation_gain_meters: float | None = None
    avg_speed: float | None = None
    avg_heartrate: float | None = None
    max_heartrate: float | None = None
    calories: int | None = None


class ActivityListResponse(BaseModel):
    items: list[ActivitySummary]
    total: int
    page: int
    page_size: int


class ActivityStats(BaseModel):
    total_distance_meters: float = 0
    total_duration_seconds: float = 0
    total_elevation_gain_meters: float = 0
    activity_count: int = 0
    sport_breakdown: dict[str, int] = Field(default_factory=dict)


class EddingtonDistributionPoint(BaseModel):
    distance_miles: float
    activity_count: int


class EddingtonResponse(BaseModel):
    eddington_number: int
    next_milestone: int
    activities_qualified_for_next: int
    activities_needed_for_next: int
    sport_breakdown: dict[str, int] = Field(default_factory=dict)
    distribution: list[EddingtonDistributionPoint] = Field(default_factory=list)
    recent_qualifying: list[ActivitySummary] = Field(default_factory=list)


class PeriodStats(BaseModel):
    distance_meters: float = 0
    duration_seconds: float = 0
    elevation_gain_meters: float = 0
    activity_count: int = 0


class SportBreakdown(BaseModel):
    sport_type: str
    distance_meters: float = 0
    duration_seconds: float = 0
    activity_count: int = 0


class DashboardResponse(BaseModel):
    week: PeriodStats
    month: PeriodStats
    year: PeriodStats
    all_time: PeriodStats
    by_sport: list[SportBreakdown]
    recent: list[ActivitySummary]


class MonthlyDay(BaseModel):
    distance_meters: float = 0
    duration_seconds: float = 0
    elevation_gain_meters: float = 0
    activity_count: int = 0
    activities: list[ActivitySummary] = []


class MonthlyResponse(BaseModel):
    year: int
    month: int
    days: dict[str, MonthlyDay]
    total_distance_meters: float = 0
    total_duration_seconds: float = 0
    total_elevation_gain_meters: float = 0
    activity_count: int = 0


class VolumePeriod(BaseModel):
    period_start: str
    distance_meters: float = 0
    duration_seconds: float = 0
    elevation_gain_meters: float = 0
    activity_count: int = 0


class PersonalRecords(BaseModel):
    longest_distance_meters: ActivitySummary | None = None
    longest_duration_seconds: ActivitySummary | None = None
    highest_elevation_gain_meters: ActivitySummary | None = None
    fastest_avg_speed: ActivitySummary | None = None
    highest_avg_heartrate: ActivitySummary | None = None
    highest_calories: ActivitySummary | None = None
    max_speed: ActivitySummary | None = None


class YearMonthSummary(BaseModel):
    month: int
    distance_meters: float = 0
    duration_seconds: float = 0
    elevation_gain_meters: float = 0
    activity_count: int = 0


class YearInReview(BaseModel):
    year: int
    total_distance_meters: float = 0
    total_duration_seconds: float = 0
    total_elevation_gain_meters: float = 0
    activity_count: int = 0
    by_sport: list[SportBreakdown] = []
    monthly: list[YearMonthSummary] = []
    personal_records: PersonalRecords = Field(default_factory=PersonalRecords)
    favorite_month: str | None = None
    favorite_sport: str | None = None


class GearStats(BaseModel):
    id: int
    name: str
    gear_type: str
    brand: str | None = None
    model: str | None = None
    nickname: str | None = None
    retired: bool = False
    total_distance_meters: float = 0
    total_duration_seconds: float = 0
    total_elevation_gain_meters: float = 0
    activity_count: int = 0
    last_used: str | None = None
    maintenance_interval_km: float | None = None
    maintenance_overdue: bool = False


class YearResponse(BaseModel):
    available_years: list[int] = []


class StatisticsOverview(BaseModel):
    activity_count: int = 0
    total_distance_meters: float = 0
    total_duration_seconds: float = 0
    total_elevation_gain_meters: float = 0
    avg_distance_meters: float = 0
    avg_duration_seconds: float = 0
    avg_speed: float = 0
