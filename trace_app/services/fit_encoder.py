from __future__ import annotations

from datetime import datetime, timezone

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.workout_message import WorkoutMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import (
    FileType,
    Intensity,
    Sport,
    WorkoutStepDuration,
    WorkoutStepTarget,
)

SPORT_TO_FIT = {
    "ride": Sport.CYCLING,
    "run": Sport.RUNNING,
    "swim": Sport.SWIMMING,
    "hike": Sport.HIKING,
    "walk": Sport.WALKING,
}

INTENSITY = {
    "rest": Intensity.REST,
    "warmup": Intensity.WARMUP,
    "cooldown": Intensity.COOLDOWN,
}

SECS_PER_MIN = 60
SECS_PER_HOUR = 3600


def _dur_secs(duration: dict | None) -> int:
    if not duration:
        return 0
    unit = duration.get("unit", "min")
    val = duration.get("value", 0)
    if unit == "s":
        return int(val)
    if unit == "min":
        return int(val * SECS_PER_MIN)
    if unit == "h":
        return int(val * SECS_PER_HOUR)
    if unit == "km":
        return int(val * 1000)
    if unit == "mi":
        return int(val * 1609)
    if unit == "m":
        return int(val)
    return int(val * SECS_PER_MIN)


def encode_workout_fit(
    steps: list[dict],
    sport: str = "other",
    name: str = "",
    scheduled_date: datetime | None = None,
) -> bytes:
    flat: list[dict] = []
    for s in steps:
        stype = s.get("type", "")
        if stype == "repeat" and s.get("steps"):
            for _ in range(s.get("repetitions", 1) or 1):
                inner = s["steps"]
                if st := inner[0].get("type") if len(inner) == 1 else None:
                    if st == "repeat_group":
                        flat.extend(inner[0].get("steps", []))
                    else:
                        flat.append(inner[0])
                else:
                    flat.extend(inner)
        else:
            flat.append(s)

    if not flat:
        flat = [{"type": "open", "duration": None, "target": None,
                 "name": name or "Workout"}]

    num_steps = min(len(flat), 100)

    builder = FitFileBuilder(auto_define=True, min_string_size=50)

    # File ID
    file_id = FileIdMessage()
    file_id.type = FileType.WORKOUT
    file_id.manufacturer = 255  # development
    file_id.product = 0
    if scheduled_date:
        epoch = scheduled_date.replace(tzinfo=timezone.utc) if scheduled_date.tzinfo is None else scheduled_date
        file_id.time_created = round(epoch.timestamp() * 1000)
    else:
        file_id.time_created = round(datetime.now(timezone.utc).timestamp() * 1000)
    builder.add(file_id)

    # Workout
    fit_sport = SPORT_TO_FIT.get(sport, Sport.GENERIC)
    workout = WorkoutMessage()
    workout.sport = fit_sport
    workout.num_valid_steps = num_steps
    workout.workout_name = name[:50] if name else ""
    builder.add(workout)

    # Subfield helper (workaround for fit-tool SubField.is_valid bug)
    def _set_duration(msg, raw_val, unit_is_dist):
        dur_field = msg.get_field(2)
        if raw_val == 0 or msg.get_field(1).get_value() == 5:  # OPEN
            dur_field.set_value(0, 0)
            return
        if unit_is_dist:
            sf = next((s for s in dur_field.sub_fields if s.name == "duration_distance"), None)
            dur_field.set_value(0, float(raw_val), sf)
        else:
            sf = next((s for s in dur_field.sub_fields if s.name == "duration_time"), None)
            dur_field.set_value(0, float(raw_val), sf)

    # Workout Steps
    for idx, s in enumerate(flat[:100]):
        step_type_name = s.get("type", "")
        step = WorkoutStepMessage()
        step.message_index = idx
        step.workout_step_name = (s.get("name") or "")[:255]

        duration = s.get("duration") or s.get("distance")
        raw_dur = _dur_secs(duration) if duration else 0
        unit = (duration or {}).get("unit", "") if duration else ""
        dist_units = {"km", "mi", "m"}
        if raw_dur == 0 or step_type_name == "open":
            step.duration_type = WorkoutStepDuration.OPEN
        elif unit in dist_units:
            step.duration_type = WorkoutStepDuration.DISTANCE
        else:
            step.duration_type = WorkoutStepDuration.TIME
        _set_duration(step, raw_dur, unit in dist_units)

        target = s.get("target")
        if target:
            ttype = target.get("type", "")
            if ttype == "power_zone":
                step.target_type = WorkoutStepTarget.POWER
                step.target_power_zone = target.get("zone", 2)
            elif ttype == "hr_zone":
                step.target_type = WorkoutStepTarget.HEART_RATE
                step.target_hr_zone = target.get("zone", 2)
            elif ttype == "power_percent":
                step.target_type = WorkoutStepTarget.POWER
                step.target_value = int(target.get("value", 70))
            elif ttype == "hr_percent":
                step.target_type = WorkoutStepTarget.HEART_RATE
                step.target_value = int(target.get("value", 70))
            elif ttype == "pace":
                step.target_type = WorkoutStepTarget.SPEED
                pace = float(target.get("value", 0))
                if pace > 0:
                    speed_mms = int(1000.0 / (pace * 60.0) * 1000)
                    step.target_value = speed_mms
            elif ttype == "speed":
                step.target_type = WorkoutStepTarget.SPEED
                kmh = float(target.get("value", 0))
                step.target_value = int(kmh / 3.6 * 1000)

        step.intensity = INTENSITY.get(step_type_name, Intensity.ACTIVE)

        builder.add(step)

    fit_file = builder.build()
    return fit_file.to_bytes()
