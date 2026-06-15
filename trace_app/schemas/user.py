import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    preferred_units: str | None = Field(default=None, max_length=20)
    weight_kg: float | None = None
    ftp_watts: int | None = None
    max_hr: int | None = None
    resting_hr: int | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str | None = None
    preferred_units: str
    weight_kg: float | None = None
    ftp_watts: int | None = None
    is_admin: bool = False
    max_hr: int | None = None
    resting_hr: int | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
