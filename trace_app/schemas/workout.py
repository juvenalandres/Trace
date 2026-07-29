from __future__ import annotations

from pydantic import BaseModel, Field


class Duration(BaseModel):
    value: float
    unit: str = Field(max_length=10)


class Distance(BaseModel):
    value: float
    unit: str = Field(max_length=10)


class IntensityTarget(BaseModel):
    type: str = Field(max_length=50)
    value: float | None = None
    unit: str | None = Field(default=None, max_length=20)
    of: str | None = Field(default=None, max_length=20)
    zone: int | None = Field(default=None, ge=1, le=5)


class WorkoutStep(BaseModel):
    type: str = Field(max_length=50)
    name: str | None = Field(default=None, max_length=255)
    duration: Duration | None = None
    distance: Distance | None = None
    target: IntensityTarget | None = None
    repetitions: int | None = Field(default=None, ge=1)
    steps: list[WorkoutStep] | None = None
    notes: str | None = None


class WorkoutBlock(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    steps: list[WorkoutStep] = []


class Workout(BaseModel):
    blocks: list[WorkoutBlock] = []


WorkoutStep.model_rebuild()


def validate_interval_json(v: str | None) -> str | None:
    """Validate the intervals string — must be None, legacy text, or valid Workout JSON."""
    if v is None:
        return v
    import json
    try:
        data = json.loads(v)
        if isinstance(data, dict):
            Workout.model_validate(data)
    except json.JSONDecodeError:
        pass
    return v


def parse_interval_json(v: str | None) -> dict | None:
    """Try to parse intervals as Workout JSON. Returns the workout dict or None."""
    if v is None:
        return None
    import json
    try:
        data = json.loads(v)
        if isinstance(data, dict):
            validated = Workout.model_validate(data)
            return validated.model_dump(mode="json")
    except (json.JSONDecodeError, Exception):
        pass
    return None
