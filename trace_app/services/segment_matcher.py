import logging
from pathlib import Path

from haversine import Unit, haversine
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trace_app.config import settings
from trace_app.models import Activity, Segment
from trace_app.models.segment_effort import SegmentEffort
from trace_app.services.gpx_parser import TrackPoint, parse_gpx

logger = logging.getLogger(__name__)

DEFAULT_MATCH_RADIUS_M = 50


def _interp_closest(
    p1_lat: float, p1_lng: float,
    p2_lat: float, p2_lng: float,
    t_lat: float, t_lng: float,
) -> tuple[float, float, float]:
    """Find the point on segment p1→p2 closest to target.
    Returns (lat, lng, t) where t ∈ [0,1] is the interpolation parameter."""
    dy = p2_lat - p1_lat
    dx = p2_lng - p1_lng
    len_sq = dx * dx + dy * dy
    if len_sq == 0:
        return p1_lat, p1_lng, 0.0
    t = max(0.0, min(1.0, ((t_lng - p1_lng) * dx + (t_lat - p1_lat) * dy) / len_sq))
    return p1_lat + t * dy, p1_lng + t * dx, t


def _parse_activity_raw_file(file_path: str) -> list[TrackPoint] | None:
    """Parse a stored raw file (GPX or FIT) back into TrackPoints."""
    path = Path(file_path)
    if not path.exists():
        return None
    try:
        content = path.read_bytes()
        if file_path.lower().endswith(".gpx"):
            return parse_gpx(content)
        elif file_path.lower().endswith(".fit"):
            from trace_app.services.fit_parser import parse_fit
            result = parse_fit(content)
            return result.points
        return None
    except Exception as e:
        logger.warning(f"Failed to reparse {file_path}: {e}")
        return None


async def match_activities_for_segment(
    db: AsyncSession,
    segment: Segment,
    limit: int = 500,
) -> list[SegmentEffort]:
    """After creating a new segment, scan existing activities with raw files for matches."""
    radius_m = getattr(settings, "segment_match_radius_m", DEFAULT_MATCH_RADIUS_M)

    q = select(Activity).where(Activity.raw_file_path.isnot(None))
    if segment.sport_type:
        q = q.where(Activity.sport_type == segment.sport_type)
    q = q.order_by(Activity.start_time.desc()).limit(limit)

    activities = (await db.execute(q)).scalars().all()
    if not activities:
        return []

    efforts = []
    for activity in activities:
        points = _parse_activity_raw_file(activity.raw_file_path)
        if not points or len(points) < 2:
            continue

        matched = _try_match_segment(
            segment, points, activity.id, activity.user_id, activity.start_time, radius_m
        )
        for effort in matched:
            existing_q = select(SegmentEffort).where(
                SegmentEffort.segment_id == segment.id,
                SegmentEffort.activity_id == activity.id,
                SegmentEffort.start_time == effort.start_time,
            )
            existing = (await db.execute(existing_q)).scalar_one_or_none()
            if existing is None:
                db.add(effort)
                efforts.append(effort)

    if efforts:
        await db.flush()

    return efforts


async def match_segments_for_activity(
    db: AsyncSession,
    points: list[TrackPoint],
    activity_id: int,
    user_id: int,
    sport_type: str,
    start_time,
) -> list[SegmentEffort]:
    if not points or len(points) < 2:
        return []

    radius_m = getattr(settings, "segment_match_radius_m", DEFAULT_MATCH_RADIUS_M)
    max_segments = getattr(settings, "segment_match_max", 5000)

    seg_q = select(Segment).limit(max_segments)
    if sport_type:
        seg_q = seg_q.where(
            (Segment.sport_type.is_(None)) | (Segment.sport_type == sport_type)
        )

    segments = (await db.execute(seg_q)).scalars().all()
    if not segments:
        return []

    efforts = []
    for seg in segments:
        matched = _try_match_segment(
            seg, points, activity_id, user_id, start_time, radius_m
        )
        for effort in matched:
            existing_q = select(SegmentEffort).where(
                SegmentEffort.segment_id == seg.id,
                SegmentEffort.activity_id == activity_id,
                SegmentEffort.start_time == effort.start_time,
            )
            existing = (await db.execute(existing_q)).scalar_one_or_none()
            if existing is None:
                db.add(effort)
                efforts.append(effort)

    if efforts:
        await db.flush()

    return efforts


def _try_match_segment(
    seg: Segment,
    points: list[TrackPoint],
    activity_id: int,
    user_id: int,
    start_time,
    radius_m: float,
) -> list[SegmentEffort]:
    if seg.distance_m is None or seg.distance_m <= 0:
        return []

    tolerance = 0.10
    results: list[SegmentEffort] = []
    idx = 0

    while idx < len(points) - 1:
        p1, p2 = points[idx], points[idx + 1]
        _, _, t_start = _interp_closest(
            p1.lat, p1.lng, p2.lat, p2.lng,
            seg.start_lat, seg.start_lng,
        )
        s_lat = p1.lat + t_start * (p2.lat - p1.lat)
        s_lng = p1.lng + t_start * (p2.lng - p1.lng)
        if haversine((s_lat, s_lng), (seg.start_lat, seg.start_lng), unit=Unit.METERS) > radius_m:
            idx += 1
            continue

        best_ei = None
        best_t_end = None
        best_ratio = float("inf")
        best_effort = None
        for ei in range(idx + 1, len(points) - 1):
            q1, q2 = points[ei], points[ei + 1]
            _, _, t_end = _interp_closest(
                q1.lat, q1.lng, q2.lat, q2.lng,
                seg.end_lat, seg.end_lng,
            )
            e_lat = q1.lat + t_end * (q2.lat - q1.lat)
            e_lng = q1.lng + t_end * (q2.lng - q1.lng)
            if haversine((e_lat, e_lng), (seg.end_lat, seg.end_lng), unit=Unit.METERS) > radius_m:
                continue

            start_dt = p1.time + t_start * (p2.time - p1.time) if p1.time and p2.time else None
            end_dt = q1.time + t_end * (q2.time - q1.time) if q1.time and q2.time else None

            elapsed_s = 0.0
            if start_dt and end_dt:
                elapsed_s = (end_dt - start_dt).total_seconds()
                if elapsed_s <= 0:
                    continue

            d_start_to_p2 = (1.0 - t_start) * haversine(
                (p1.lat, p1.lng), (p2.lat, p2.lng), unit=Unit.METERS
            )
            total_dist = d_start_to_p2
            hrs = []
            powers = []
            for i in range(idx + 2, ei + 1):
                prev, cur = points[i - 1], points[i]
                d = haversine((prev.lat, prev.lng), (cur.lat, cur.lng), unit=Unit.METERS)
                total_dist += d
                if cur.hr:
                    hrs.append(cur.hr)
                if cur.power:
                    powers.append(cur.power)
            d_q1_to_end = t_end * haversine(
                (q1.lat, q1.lng), (q2.lat, q2.lng), unit=Unit.METERS
            )
            total_dist += d_q1_to_end

            ratio = abs(total_dist - seg.distance_m) / seg.distance_m
            if ratio > tolerance or ratio >= best_ratio:
                continue

            avg_speed = (total_dist / elapsed_s) if elapsed_s > 0 else None
            avg_hr = sum(hrs) / len(hrs) if hrs else None
            avg_power = sum(powers) / len(powers) if powers else None

            best_ratio = ratio
            best_ei = ei
            best_t_end = t_end
            best_effort = SegmentEffort(
                segment_id=seg.id,
                activity_id=activity_id,
                user_id=user_id,
                elapsed_time_s=elapsed_s,
                avg_speed=round(avg_speed, 2) if avg_speed else None,
                avg_hr=round(avg_hr, 1) if avg_hr else None,
                avg_power=round(avg_power, 1) if avg_power else None,
                start_time=start_dt or start_time,
            )

        if best_ei is not None:
            results.append(best_effort)
            idx = best_ei + 1
        else:
            idx += 1

    return results
