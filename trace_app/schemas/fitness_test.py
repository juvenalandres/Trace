import datetime

from pydantic import BaseModel, ConfigDict, Field


class FitnessTestCreate(BaseModel):
    test_type: str = Field(max_length=50)
    value: float
    unit: str = Field(max_length=20)
    start_time: datetime.datetime
    end_time: datetime.datetime
    notes: str | None = None


class FitnessTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    test_type: str
    value: float
    unit: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    fit_file_path: str | None = None
    notes: str | None = None
    created_at: datetime.datetime


class FitnessTestChartData(BaseModel):
    timestamps: list[float]
    power: list[float | None]
    hr: list[float | None]
    elevation: list[float | None]
    speed: list[float | None]
    fit_start_time: str | None = None
