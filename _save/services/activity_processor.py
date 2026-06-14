import json
import xml.etree.ElementTree as ET
from datetime import datetime

from haversine import Unit, haversine
from simplification.cutil import simplify_coords

Point = tuple[float, float, float | None, datetime | None, int | None, int | None]


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def parse_gpx_content(content: str | bytes) -> list[Point]:
    root = ET.fromstring(content) if isinstance(content, str) else ET.fromstring(content.decode())
    points: list[Point] = []

    for trkpt in root.iter():
        if _strip_ns(trkpt.tag) != "trkpt":
            continue

        lat = float(trkpt.get("lat"))
        lng = float(trkpt.get("lon"))

        ele: float | None = None
        time: datetime | None = None
        hr: int | None = None
        cad: int | None = None

        for child in trkpt:
            tag = _strip_ns(child.tag)
            if tag == "ele" and child.text:
                ele = float(child.text)
            elif tag == "time" and child.text:
                time = datetime.fromisoformat(child.text.replace("Z", "+00:00"))
            elif tag == "extensions":
                for ext_child in child:
                    if _strip_ns(ext_child.tag) == "TrackPointExtension":
                        for tpe_child in ext_child:
                            t = _strip_ns(tpe_child.tag)
                            if t == "hr" and tpe_child.text:
                                hr = int(tpe_child.text)
                            elif t == "cad" and tpe_child.text:
                                cad = int(tpe_child.text)

        points.append((lat, lng, ele, time, hr, cad))
    return points


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return haversine((lat1, lng1), (lat2, lng2), unit=Unit.METERS)


def compute_stats(points: list[Point]) -> dict:
    if len(points) < 2:
        return {
            "distance_meters": 0.0,
            "duration_seconds": 0.0,
            "elevation_gain_meters": 0.0,
            "elevation_loss_meters": 0.0,
            "avg_speed": 0.0,
            "max_speed": 0.0,
            "avg_heartrate": None,
            "max_heartrate": None,
        }

    total_distance = 0.0
    total_elevation_gain = 0.0
    total_elevation_loss = 0.0
    max_speed_ms = 0.0
    heartrates = []

    for i in range(1, len(points)):
        lat1, lng1, _, _, _, _ = points[i - 1]
        lat2, lng2, _, _, _, _ = points[i]

        dist = haversine_distance(lat1, lng1, lat2, lng2)
        total_distance += dist

        _, _, elev1, time1, hr1, _ = points[i - 1]
        _, _, elev2, time2, hr2, _ = points[i]

        if elev1 is not None and elev2 is not None:
            diff = elev2 - elev1
            if diff > 0:
                total_elevation_gain += diff
            else:
                total_elevation_loss += abs(diff)

        if time1 is not None and time2 is not None:
            time_diff = (time2 - time1).total_seconds()
            if time_diff > 0:
                speed_ms = dist / time_diff
                max_speed_ms = max(max_speed_ms, speed_ms)

        if hr1 is not None:
            heartrates.append(hr1)

    if heartrates and points[-1][4] is not None:
        heartrates.append(points[-1][4])

    first_time = points[0][3]
    last_time = points[-1][3]
    duration = 0.0
    if first_time is not None and last_time is not None:
        duration = (last_time - first_time).total_seconds()

    avg_speed = (total_distance / duration) if duration > 0 else 0.0

    return {
        "distance_meters": round(total_distance, 2),
        "duration_seconds": round(duration, 1),
        "elevation_gain_meters": round(total_elevation_gain, 1),
        "elevation_loss_meters": round(total_elevation_loss, 1),
        "avg_speed": round(avg_speed, 2),
        "max_speed": round(max_speed_ms, 2),
        "avg_heartrate": round(sum(heartrates) / len(heartrates), 1) if heartrates else None,
        "max_heartrate": max(heartrates) if heartrates else None,
    }


def encode_polyline(points: list[tuple[float, float]]) -> str:
    import polyline as pl

    return pl.encode([(lat, lng) for lat, lng in points])


def simplify_route(
    points: list[tuple[float, float]], tolerance: float = 0.0001
) -> list[tuple[float, float]]:
    coords = [[lng, lat] for lat, lng in points]
    simplified = simplify_coords(coords, tolerance)
    return [(lat, lng) for lng, lat in simplified]


def build_elevation_profile(points: list[Point]) -> list[list[float]]:
    profile = []
    cumulative = 0.0
    for i, (lat, lng, elev, *_) in enumerate(points):
        if i > 0:
            prev_lat, prev_lng, _, _, _, _ = points[i - 1]
            cumulative += haversine_distance(prev_lat, prev_lng, lat, lng)
        if elev is not None:
            profile.append([round(cumulative, 1), round(elev, 1)])
    return profile


def build_time_series(points: list[Point]) -> list[dict]:
    series = []
    cumulative = 0.0
    for i, (lat, lng, elev, time, hr, _cad) in enumerate(points):
        spd = None
        if i > 0:
            prev_lat, prev_lng, _, prev_time, _, _ = points[i - 1]
            seg = haversine_distance(prev_lat, prev_lng, lat, lng)
            cumulative += seg
            if time is not None and prev_time is not None:
                dt = (time - prev_time).total_seconds()
                if dt > 0:
                    spd = round(seg / dt, 2)
        series.append({
            "d": round(cumulative, 1),
            "ele": round(elev, 1) if elev is not None else None,
            "spd": spd,
            "hr": hr,
            "lat": lat,
            "lng": lng,
        })
    series[0]["d"] = 0.0
    return series


def process_gpx_points(points: list[Point]) -> dict:
    stats = compute_stats(points)
    lng_lat_points = [(lat, lng) for lat, lng, _, _, _, _ in points]

    simplified = simplify_route(lng_lat_points) if len(points) > 100 else lng_lat_points
    polyline = encode_polyline(simplified)
    elevation_profile = build_elevation_profile(points)
    time_series = build_time_series(points)

    lats = [lat for lat, _, _, _, _, _ in points]
    lngs = [lng for _, lng, _, _, _, _ in points]

    return {
        **stats,
        "polyline": polyline,
        "elevation_profile": json.dumps(elevation_profile) if elevation_profile else None,
        "time_series": json.dumps(time_series) if time_series else None,
        "min_lat": min(lats),
        "max_lat": max(lats),
        "min_lng": min(lngs),
        "max_lng": max(lngs),
    }
