import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionTarget(BaseModel):
    type: str = Field(max_length=50)
    value: float | None = None
    unit: str | None = Field(default=None, max_length=20)


class TrainingSessionCreate(BaseModel):
    scheduled_date: datetime.date
    sport_type: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    targets: list[SessionTarget] = []
    intervals: str | None = Field(default=None, max_length=10000)
    notes: str | None = Field(default=None, max_length=10000)
    rest_day: bool = False


class TrainingSessionUpdate(BaseModel):
    scheduled_date: datetime.date | None = None
    sport_type: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    targets: list[SessionTarget] | None = None
    intervals: str | None = Field(default=None, max_length=10000)
    notes: str | None = Field(default=None, max_length=10000)
    rest_day: bool | None = None
    status: str | None = Field(default=None, max_length=20)


class TrainingSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    scheduled_date: datetime.date
    sport_type: str | None = None
    name: str | None = None
    description: str | None = None
    targets: list[SessionTarget] = []
    intervals: str | None = None
    notes: str | None = None
    rest_day: bool = False
    activity_id: int | None = None
    status: str
    created_at: datetime.datetime


class TrainingPlanCreate(BaseModel):
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None


class TrainingPlanUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None


class TrainingPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    created_at: datetime.datetime
    sessions: list[TrainingSessionResponse] = []
