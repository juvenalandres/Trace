import json
from datetime import datetime

from haversine import Unit, haversine
from simplification.cutil import simplify_coords

from trace_app.config import settings
from trace_app.models.enums import SportType
from trace_app.services.gpx_parser import TrackPoint


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return haversine((lat1, lng1), (lat2, lng2), unit=Unit.METERS)


def compute_stats(points: list[TrackPoint]) -> dict:
    if len(points) < 2:
        return {
            "distance_m": 0.0,
            "duration_s": 0.0,
            "moving_time_s": 0.0,
            "elevation_gain": 0.0,
            "elevation_loss": 0.0,
            "avg_speed": 0.0,
            "max_speed": 0.0,
            "avg_hr": None,
            "max_hr": None,
            "avg_power": None,
            "max_power": None,
            "avg_cadence": None,
            "calories": None,
            "avg_temp": None,
        }

    total_distance = 0.0
    total_elevation_gain = 0.0
    total_elevation_loss = 0.0
    max_speed_ms = 0.0
    moving_time = 0.0
    heartrates: list[int] = []
    powers: list[int] = []
    cadences: list[int] = []
    temps: list[float] = []

    for i in range(1, len(points)):
        p_prev = points[i - 1]
        p_curr = points[i]

        dist = haversine_distance(p_prev.lat, p_prev.lng, p_curr.lat, p_curr.lng)
        total_distance += dist

        if p_prev.ele is not None and p_curr.ele is not None:
            diff = p_curr.ele - p_prev.ele
            if diff > 0:
                total_elevation_gain += diff
            else:
                total_elevation_loss += abs(diff)

        if p_prev.time is not None and p_curr.time is not None:
            time_diff = (p_curr.time - p_prev.time).total_seconds()
            if time_diff > 0:
                speed_ms = p_curr.speed if p_curr.speed is not None else dist / time_diff
                max_speed_ms = max(max_speed_ms, speed_ms)
                if speed_ms > 0.5:
                    moving_time += time_diff

    for p in points:
        if p.hr is not None:
            heartrates.append(p.hr)
        if p.power is not None:
            powers.append(p.power)
        if p.cadence is not None:
            cadences.append(p.cadence)
        if p.temp is not None:
            temps.append(p.temp)

    first_time = points[0].time
    last_time = points[-1].time
    duration = 0.0
    if first_time is not None and last_time is not None:
        duration = (last_time - first_time).total_seconds()

    avg_speed = (total_distance / duration) if duration > 0 else 0.0

    return {
        "distance_m": round(total_distance, 2),
        "duration_s": round(duration, 1),
        "moving_time_s": round(moving_time, 1),
        "elevation_gain": round(total_elevation_gain, 1),
        "elevation_loss": round(total_elevation_loss, 1),
        "avg_speed": round(avg_speed, 2),
        "max_speed": round(max_speed_ms, 2),
        "avg_hr": round(sum(heartrates) / len(heartrates), 1) if heartrates else None,
        "max_hr": max(heartrates) if heartrates else None,
        "avg_power": round(sum(powers) / len(powers), 1) if powers else None,
        "max_power": max(powers) if powers else None,
        "avg_cadence": round(sum(cadences) / len(cadences), 1) if cadences else None,
        "calories": None,
        "avg_temp": round(sum(temps) / len(temps), 1) if temps else None,
    }


def encode_polyline(points: list[TrackPoint]) -> str:
    import polyline as pl
    return pl.encode([(p.lat, p.lng) for p in points])


def simplify_route(points: list[TrackPoint], tolerance: float = 0.0001) -> list[TrackPoint]:
    if len(points) <= 100:
        return points
    coords = [[p.lng, p.lat] for p in points]
    simplified = simplify_coords(coords, tolerance)
    simplified_set = {(round(lng, 6), round(lat, 6)) for lat, lng in simplified}
    return [p for p in points if (round(p.lng, 6), round(p.lat, 6)) in simplified_set]


def build_elevation_profile(points: list[TrackPoint]) -> list[list[float]]:
    profile = []
    cumulative = 0.0
    for i, p in enumerate(points):
        if i > 0:
            prev = points[i - 1]
            cumulative += haversine_distance(prev.lat, prev.lng, p.lat, p.lng)
        if p.ele is not None:
            profile.append([round(cumulative, 1), round(p.ele, 1)])
    return profile


def build_simplified_time_series(
    points: list[TrackPoint], bucket_s: int | None = None
) -> list[dict]:
    if bucket_s is None:
        bucket_s = settings.simplified_time_series_bucket_s
    if not points or bucket_s <= 0:
        return []

    first_time = None
    for p in points:
        if p.time is not None:
            first_time = p.time
            break

    if first_time is None:
        nth = max(1, bucket_s)
        series = []
        cumulative = 0.0
        for i, p in enumerate(points):
            if i > 0:
                prev = points[i - 1]
                seg = haversine_distance(prev.lat, prev.lng, p.lat, p.lng)
                cumulative += seg
            if i % nth == 0 or i == len(points) - 1:
                spd = None
                pace = None
                if i > 0 and p.time is not None and points[i - 1].time is not None:
                    prev = points[i - 1]
                    dt = (p.time - prev.time).total_seconds()
                    seg = haversine_distance(prev.lat, prev.lng, p.lat, p.lng)
                    if dt > 0:
                        spd = round(seg / dt, 2)
                        if seg > 0:
                            pace = round((dt / seg) * 1000 / 60, 2)
                series.append({
                    "d": round(cumulative, 1),
                    "ele": round(p.ele, 1) if p.ele is not None else None,
                    "spd": spd, "pace": pace,
                    "hr": p.hr, "pwr": p.power, "cad": p.cadence,
                    "lat": p.lat, "lng": p.lng,
                })
        return series

    cum_dists = [0.0]
    for i in range(1, len(points)):
        seg = haversine_distance(points[i - 1].lat, points[i - 1].lng, points[i].lat, points[i].lng)
        cum_dists.append(cum_dists[-1] + seg)

    buckets: dict[int, list[int]] = {}
    for i, p in enumerate(points):
        if p.time is not None:
            bidx = int((p.time - first_time).total_seconds() // bucket_s)
        else:
            bidx = 0
        buckets.setdefault(bidx, []).append(i)

    # Build intermediate rows: averaged fields + cumulative distance at bucket end + midpoint time
    rows: list[dict] = []
    for bidx in sorted(buckets):
        indices = buckets[bidx]
        last_idx = indices[-1]
        first_idx = indices[0]
        end_dist = cum_dists[last_idx]
        first_pt = points[first_idx]
        last_pt = points[last_idx]

        n = len(indices)
        avg_lat = sum(points[idx].lat for idx in indices) / n
        avg_lng = sum(points[idx].lng for idx in indices) / n

        eles = [points[idx].ele for idx in indices if points[idx].ele is not None]
        hrs = [points[idx].hr for idx in indices if points[idx].hr is not None]
        pwrs = [points[idx].power for idx in indices if points[idx].power is not None]
        cads = [points[idx].cadence for idx in indices if points[idx].cadence is not None]

        mid_time = None
        if first_pt.time is not None and last_pt.time is not None:
            mid_dt = (last_pt.time - first_pt.time).total_seconds() / 2
            mid_time = first_pt.time.timestamp() + mid_dt

        rows.append({
            "d": end_dist,
            "ele": sum(eles) / len(eles) if eles else None,
            "hr": sum(hrs) / len(hrs) if hrs else None,
            "pwr": sum(pwrs) / len(pwrs) if pwrs else None,
            "cad": sum(cads) / len(cads) if cads else None,
            "lat": avg_lat,
            "lng": avg_lng,
            "t": mid_time,
        })

    # Compute speed/pace between consecutive output points
    series = []
    for i, row in enumerate(rows):
        spd = 0.0
        pace = 0.0
        if i > 0:
            prev = rows[i - 1]
            d_dist = row["d"] - prev["d"]
            t_delta = 0.0
            if row["t"] is not None and prev["t"] is not None:
                t_delta = row["t"] - prev["t"]
            if t_delta > 0:
                spd = d_dist / t_delta
                if d_dist > 0:
                    pace = (t_delta / d_dist) * 1000 / 60

        series.append({
            "d": round(row["d"], 1),
            "ele": round(row["ele"], 1) if row["ele"] is not None else None,
            "spd": round(spd, 2),
            "pace": round(pace, 2),
            "hr": round(row["hr"]) if row["hr"] is not None else None,
            "pwr": round(row["pwr"]) if row["pwr"] is not None else None,
            "cad": round(row["cad"]) if row["cad"] is not None else None,
            "lat": round(row["lat"], 6),
            "lng": round(row["lng"], 6),
        })

    return series


def generate_laps(
    points: list[TrackPoint], interval_meters: float = 1000.0
) -> list[dict]:
    if len(points) < 2:
        return []

    laps = []
    lap_start_idx = 0
    cumulative = 0.0
    lap_distance = 0.0

    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]
        seg = haversine_distance(prev.lat, prev.lng, curr.lat, curr.lng)
        cumulative += seg
        lap_distance += seg

        if lap_distance >= interval_meters:
            lap_points = points[lap_start_idx : i + 1]
            lap = _compute_lap_stats(lap_points, len(laps), lap_distance)
            laps.append(lap)
            lap_start_idx = i
            lap_distance = 0.0

    if lap_start_idx < len(points) - 1:
        remaining = points[lap_start_idx:]
        lap_dist = sum(
            haversine_distance(
                remaining[j].lat, remaining[j].lng,
                remaining[j + 1].lat, remaining[j + 1].lng,
            )
            for j in range(len(remaining) - 1)
        )
        if lap_dist > 10:
            laps.append(_compute_lap_stats(remaining, len(laps), lap_dist))

    return laps


def _compute_lap_stats(points: list[TrackPoint], index: int, distance: float) -> dict:
    duration = 0.0
    if points[0].time is not None and points[-1].time is not None:
        duration = (points[-1].time - points[0].time).total_seconds()

    speeds: list[float] = []
    heartrates: list[int] = []
    powers: list[int] = []
    cadences: list[int] = []

    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]
        if prev.time is not None and curr.time is not None:
            dt = (curr.time - prev.time).total_seconds()
            if dt > 0:
                seg = haversine_distance(prev.lat, prev.lng, curr.lat, curr.lng)
                speed = curr.speed if curr.speed is not None else seg / dt
                speeds.append(speed)

    for p in points:
        if p.hr is not None:
            heartrates.append(p.hr)
        if p.power is not None:
            powers.append(p.power)
        if p.cadence is not None:
            cadences.append(p.cadence)

    return {
        "lap_index": index,
        "distance_m": round(distance, 2),
        "duration_s": round(duration, 1),
        "avg_speed": round(sum(speeds) / len(speeds), 2) if speeds else None,
        "max_speed": round(max(speeds), 2) if speeds else None,
        "avg_hr": round(sum(heartrates) / len(heartrates), 1) if heartrates else None,
        "max_hr": max(heartrates) if heartrates else None,
        "avg_power": round(sum(powers) / len(powers), 1) if powers else None,
        "max_power": max(powers) if powers else None,
        "avg_cadence": round(sum(cadences) / len(cadences), 1) if cadences else None,
        "calories": None,
    }


def compute_distance_splits_from_ts(
    ts_json: str, interval_m: float = 10000.0
) -> list[dict]:
    try:
        series = json.loads(ts_json)
    except (json.JSONDecodeError, TypeError):
        return []
    if len(series) < 2:
        return []

    total_distance_m = series[-1]["d"] or 0.0
    if total_distance_m < interval_m:
        return []

    splits = []
    next_split = interval_m
    cumul_time = 0.0
    prev_d = series[0]["d"] or 0.0

    for i in range(1, len(series)):
        curr_d = series[i]["d"] or 0.0
        seg_d = curr_d - prev_d
        spd = series[i].get("spd") or 0
        if seg_d > 0 and spd > 0:
            cumul_time += seg_d / spd

        while curr_d >= next_split:
            t_before = cumul_time - (seg_d / spd) if seg_d > 0 and spd > 0 else cumul_time
            frac = (next_split - prev_d) / seg_d if seg_d > 0 else 0
            split_time = t_before + frac * (cumul_time - t_before)

            prev_split_km = next_split / 1000 - interval_m / 1000
            prev_time = next(
                (s["cumulative_time_s"] for s in reversed(splits) if abs(s["split_km"] - prev_split_km) < 0.01),
                0.0
            ) if prev_split_km > 0 else 0.0
            seg_time = split_time - prev_time

            splits.append({
                "split_km": next_split / 1000,
                "cumulative_time_s": round(split_time, 1),
                "cumulative_speed_kmh": round((next_split / 1000) / (split_time / 3600), 1) if split_time > 0 else 0,
                "segment_time_s": round(seg_time, 1),
                "segment_speed_kmh": round((interval_m / 1000) / (seg_time / 3600), 1) if seg_time > 0 else 0,
            })
            next_split += interval_m

        prev_d = curr_d
        if next_split > total_distance_m:
            break

    return splits


def process_activity(points: list[TrackPoint], session_overrides: dict | None = None) -> dict:
    stats = compute_stats(points)
    polyline = encode_polyline(points)
    elevation_profile = build_elevation_profile(points)
    simplified_ts = build_simplified_time_series(points)
    laps = generate_laps(points)

    if session_overrides:
        for key, value in session_overrides.items():
            if value is not None and key in stats:
                stats[key] = value

    lats = [p.lat for p in points]
    lngs = [p.lng for p in points]

    return {
        **stats,
        "polyline": polyline,
        "elevation_profile": json.dumps(elevation_profile) if elevation_profile else None,
        "simplified_time_series": json.dumps(simplified_ts) if simplified_ts else None,
        "min_lat": min(lats),
        "max_lat": max(lats),
        "min_lng": min(lngs),
        "max_lng": max(lngs),
        "laps": laps,
    }
