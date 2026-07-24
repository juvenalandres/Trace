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

        new_efforts = _try_match_segment(
            segment, points, activity.id, activity.user_id, activity.start_time, radius_m
        )
        for effort in new_efforts:
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
        new_efforts = _try_match_segment(
            seg, points, activity_id, user_id, start_time, radius_m
        )
        for effort in new_efforts:
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
    """Find all start→end pairs in the activity that match this segment."""
    efforts: list[SegmentEffort] = []

    idx = 0
    while idx < len(points):
        start_idx = None
        for i in range(idx, len(points)):
            dist = haversine(
                (points[i].lat, points[i].lng), (seg.start_lat, seg.start_lng), unit=Unit.METERS
            )
            if dist <= radius_m:
                start_idx = i
                break

        if start_idx is None:
            break

        end_idx = None
        for i in range(start_idx + 1, len(points)):
            dist = haversine(
                (points[i].lat, points[i].lng), (seg.end_lat, seg.end_lng), unit=Unit.METERS
            )
            if dist <= radius_m:
                end_idx = i
                break

        if end_idx is None:
            break

        seg_points = points[start_idx : end_idx + 1]
        idx = end_idx + 1

        if len(seg_points) < 2:
            continue

        elapsed_s = 0.0
        if seg_points[0].time and seg_points[-1].time:
            elapsed_s = (seg_points[-1].time - seg_points[0].time).total_seconds()
            if elapsed_s <= 0:
                continue

        total_dist = 0.0
        hrs = []
        powers = []
        for i in range(1, len(seg_points)):
            prev, cur = seg_points[i - 1], seg_points[i]
            d = haversine((prev.lat, prev.lng), (cur.lat, cur.lng), unit=Unit.METERS)
            total_dist += d
            if cur.hr:
                hrs.append(cur.hr)
            if cur.power:
                powers.append(cur.power)

        avg_speed = (total_dist / elapsed_s) if elapsed_s > 0 else None
        avg_hr = sum(hrs) / len(hrs) if hrs else None
        avg_power = sum(powers) / len(powers) if powers else None

        effort_start_time = seg_points[0].time or start_time

        efforts.append(SegmentEffort(
            segment_id=seg.id,
            activity_id=activity_id,
            user_id=user_id,
            elapsed_time_s=elapsed_s,
            avg_speed=round(avg_speed, 2) if avg_speed else None,
            avg_hr=round(avg_hr, 1) if avg_hr else None,
            avg_power=round(avg_power, 1) if avg_power else None,
            start_time=effort_start_time,
        ))

    return efforts
