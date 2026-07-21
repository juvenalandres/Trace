from dataclasses import dataclass, field
from datetime import datetime, timezone

import fitparse

from trace_app.services.gpx_parser import TrackPoint

SEMICIRCLE_TO_DEG = 180.0 / (2**31)

FIT_SPORT_MAP = {
    "cycling": "ride",
    "running": "run",
    "walking": "walk",
    "hiking": "hike",
    "swimming": "swim",
}


@dataclass
class FitSession:
    sport: str | None = None
    start_time: datetime | None = None
    total_elapsed_time: float | None = None
    total_distance: float | None = None
    total_calories: int | None = None
    total_ascent: float | None = None
    total_descent: float | None = None
    total_moving_time: float | None = None
    avg_speed: float | None = None
    max_speed: float | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_power: float | None = None
    max_power: float | None = None


@dataclass
class FitResult:
    points: list[TrackPoint]
    session: FitSession


def _get_field_value(message, field_name):
    try:
        return message.get_value(field_name)
    except Exception:
        return None


def parse_fit(content: bytes) -> FitResult:
    if len(content) > 50 * 1024 * 1024:
        raise ValueError("FIT file exceeds maximum size of 50MB")

    fitfile = fitparse.FitFile(content)

    session = FitSession()
    for msg in fitfile.get_messages("session"):
        session.sport = _get_field_value(msg, "sport")
        session.start_time = _get_field_value(msg, "start_time")
        session.total_elapsed_time = _get_field_value(msg, "total_elapsed_time")
        session.total_distance = _get_field_value(msg, "total_distance")
        session.total_calories = _get_field_value(msg, "total_calories")
        session.avg_speed = _get_field_value(msg, "enhanced_avg_speed") or _get_field_value(msg, "avg_speed")
        session.max_speed = _get_field_value(msg, "enhanced_max_speed") or _get_field_value(msg, "max_speed")
        session.total_ascent = _get_field_value(msg, "total_ascent")
        session.total_descent = _get_field_value(msg, "total_descent")
        session.total_moving_time = _get_field_value(msg, "total_moving_time")
        session.avg_hr = _get_field_value(msg, "avg_heart_rate")
        session.max_hr = _get_field_value(msg, "max_heart_rate")
        session.avg_power = _get_field_value(msg, "avg_power")
        session.max_power = _get_field_value(msg, "max_power")
        break

    if session.start_time and session.start_time.tzinfo is None:
        session.start_time = session.start_time.replace(tzinfo=timezone.utc)

    points: list[TrackPoint] = []
    last_valid_ele: float | None = None
    last_valid_hr: int | None = None
    for msg in fitfile.get_messages("record"):
        ts = _get_field_value(msg, "timestamp")
        lat_raw = _get_field_value(msg, "position_lat")
        lng_raw = _get_field_value(msg, "position_long")

        if lat_raw is None or lng_raw is None:
            continue

        lat = lat_raw * SEMICIRCLE_TO_DEG
        lng = lng_raw * SEMICIRCLE_TO_DEG

        ele = _get_field_value(msg, "enhanced_altitude") or _get_field_value(msg, "altitude")
        speed = _get_field_value(msg, "enhanced_speed") or _get_field_value(msg, "speed")
        hr = _get_field_value(msg, "heart_rate")
        cadence = _get_field_value(msg, "cadence")
        power = _get_field_value(msg, "power")
        temp = _get_field_value(msg, "temperature")

        if ts is not None and isinstance(ts, datetime) and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        ele_val: float | None = None
        if ele is not None:
            raw_ele = float(ele)
            if raw_ele >= 0:
                ele_val = raw_ele
                last_valid_ele = raw_ele
            elif last_valid_ele is not None:
                ele_val = last_valid_ele

        hr_val: int | None = None
        if hr is not None:
            hr_val = int(hr)
            last_valid_hr = hr_val
        elif last_valid_hr is not None:
            hr_val = last_valid_hr

        points.append(TrackPoint(
            lat=lat,
            lng=lng,
            ele=ele_val,
            time=ts,
            hr=hr_val,
            cadence=int(cadence) if cadence is not None else None,
            power=int(power) if power is not None else None,
            temp=float(temp) if temp is not None else None,
            speed=speed,
        ))

    return FitResult(points=points, session=session)


def map_fit_sport(sport: str | None) -> str:
    if not sport:
        return "other"
    return FIT_SPORT_MAP.get(sport.lower(), "other")
