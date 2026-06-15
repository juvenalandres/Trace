import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from trace_app.auth import get_current_user
from trace_app.database import get_db
from trace_app.models import Activity, Segment, SegmentEffort, User
from trace_app.schemas.segment import (
    SegmentCreate,
    SegmentEffortResponse,
    SegmentLeaderboardEntry,
    SegmentListResponse,
    SegmentPRResponse,
    SegmentResponse,
    SegmentUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/segments", tags=["segments"])


@router.post("", response_model=SegmentResponse)
async def create_segment(
    data: SegmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    segment = Segment(
        user_id=user.id,
        name=data.name,
        description=data.description,
        sport_type=data.sport_type,
        start_lat=data.start_lat,
        start_lng=data.start_lng,
        end_lat=data.end_lat,
        end_lng=data.end_lng,
        polyline=data.polyline,
        distance_m=data.distance_m,
        elevation_gain_m=data.elevation_gain_m,
    )
    db.add(segment)
    await db.commit()
    await db.refresh(segment)

    return SegmentResponse(
        id=segment.id,
        user_id=segment.user_id,
        creator_name=user.name or user.email,
        name=segment.name,
        description=segment.description,
        sport_type=segment.sport_type,
        start_lat=segment.start_lat,
        start_lng=segment.start_lng,
        end_lat=segment.end_lat,
        end_lng=segment.end_lng,
        polyline=segment.polyline,
        distance_m=segment.distance_m,
        elevation_gain_m=segment.elevation_gain_m,
        created_at=segment.created_at,
        best_time=None,
        effort_count=0,
    )


@router.get("", response_model=list[SegmentListResponse])
async def list_segments(
    sport_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Segment)
    if sport_type:
        q = q.where(Segment.sport_type == sport_type)
    if search:
        q = q.where(Segment.name.ilike(f"%{search}%"))
    q = q.order_by(Segment.created_at.desc())

    segments = (await db.execute(q)).scalars().all()
    if not segments:
        return []

    seg_ids = [s.id for s in segments]

    best_q = (
        select(
            SegmentEffort.segment_id,
            func.min(SegmentEffort.elapsed_time_s).label("best_time"),
            func.count(SegmentEffort.id).label("effort_count"),
        )
        .where(SegmentEffort.segment_id.in_(seg_ids))
        .group_by(SegmentEffort.segment_id)
    )
    best_rows = (await db.execute(best_q)).all()
    best_map = {r.segment_id: (r.best_time, r.effort_count) for r in best_rows}

    user_ids = list({s.user_id for s in segments})
    users_q = select(User.id, User.name, User.email).where(User.id.in_(user_ids))
    users_rows = (await db.execute(users_q)).all()
    user_map = {r.id: (r.name or r.email) for r in users_rows}

    results = []
    for s in segments:
        best_time, effort_count = best_map.get(s.id, (None, 0))
        results.append(SegmentListResponse(
            id=s.id,
            name=s.name,
            sport_type=s.sport_type,
            distance_m=s.distance_m,
            best_time=best_time,
            effort_count=effort_count,
            creator_name=user_map.get(s.user_id),
            created_at=s.created_at,
        ))
    return results


@router.get("/{segment_id}", response_model=SegmentResponse)
async def get_segment(
    segment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    seg = (await db.execute(
        select(Segment).where(Segment.id == segment_id)
    )).scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")

    creator = (await db.execute(
        select(User.name, User.email).where(User.id == seg.user_id)
    )).one_or_none()
    creator_name = (creator.name or creator.email) if creator else None

    best_q = (
        select(
            func.min(SegmentEffort.elapsed_time_s),
            func.count(SegmentEffort.id),
        )
        .where(SegmentEffort.segment_id == seg.id)
    )
    best_row = (await db.execute(best_q)).one()
    best_time = best_row[0]
    effort_count = best_row[1] or 0

    return SegmentResponse(
        id=seg.id,
        user_id=seg.user_id,
        creator_name=creator_name,
        name=seg.name,
        description=seg.description,
        sport_type=seg.sport_type,
        start_lat=seg.start_lat,
        start_lng=seg.start_lng,
        end_lat=seg.end_lat,
        end_lng=seg.end_lng,
        polyline=seg.polyline,
        distance_m=seg.distance_m,
        elevation_gain_m=seg.elevation_gain_m,
        created_at=seg.created_at,
        best_time=best_time,
        effort_count=effort_count,
    )


@router.put("/{segment_id}", response_model=SegmentResponse)
async def update_segment(
    segment_id: int,
    data: SegmentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    seg = (await db.execute(
        select(Segment).where(Segment.id == segment_id)
    )).scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")
    if seg.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the creator can update this segment")

    if data.name is not None:
        seg.name = data.name
    if data.description is not None:
        seg.description = data.description
    if data.sport_type is not None:
        seg.sport_type = data.sport_type

    await db.commit()
    await db.refresh(seg)

    creator = (await db.execute(
        select(User.name, User.email).where(User.id == seg.user_id)
    )).one_or_none()
    creator_name = (creator.name or creator.email) if creator else None

    best_q = (
        select(
            func.min(SegmentEffort.elapsed_time_s),
            func.count(SegmentEffort.id),
        )
        .where(SegmentEffort.segment_id == seg.id)
    )
    best_row = (await db.execute(best_q)).one()

    return SegmentResponse(
        id=seg.id,
        user_id=seg.user_id,
        creator_name=creator_name,
        name=seg.name,
        description=seg.description,
        sport_type=seg.sport_type,
        start_lat=seg.start_lat,
        start_lng=seg.start_lng,
        end_lat=seg.end_lat,
        end_lng=seg.end_lng,
        polyline=seg.polyline,
        distance_m=seg.distance_m,
        elevation_gain_m=seg.elevation_gain_m,
        created_at=seg.created_at,
        best_time=best_row[0],
        effort_count=best_row[1] or 0,
    )


@router.post("/{segment_id}/match")
async def match_segment_activities(
    segment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger back-matching: scan recent activities for this segment."""
    seg = (await db.execute(
        select(Segment).where(Segment.id == segment_id)
    )).scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")

    from trace_app.services.segment_matcher import match_activities_for_segment
    try:
        efforts = await match_activities_for_segment(db, seg)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Back-match failed for segment {segment_id}: {e}")
        raise HTTPException(status_code=500, detail="Back-match failed")

    return {"matched": len(efforts), "segment_id": segment_id}


@router.delete("/{segment_id}")
async def delete_segment(
    segment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    seg = (await db.execute(
        select(Segment).where(Segment.id == segment_id)
    )).scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")
    if seg.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Only the creator or admin can delete this segment")

    await db.delete(seg)
    await db.commit()
    return {"ok": True}


@router.get("/{segment_id}/efforts", response_model=list[SegmentEffortResponse])
async def list_segment_efforts(
    segment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    seg = (await db.execute(
        select(Segment.id).where(Segment.id == segment_id)
    )).scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")

    q = (
        select(SegmentEffort)
        .where(SegmentEffort.segment_id == segment_id)
        .order_by(SegmentEffort.elapsed_time_s.asc())
    )
    efforts = (await db.execute(q)).scalars().all()
    if not efforts:
        return []

    user_ids = list({e.user_id for e in efforts})
    activity_ids = list({e.activity_id for e in efforts})

    users_q = select(User.id, User.name, User.email).where(User.id.in_(user_ids))
    users_rows = (await db.execute(users_q)).all()
    user_map = {r.id: (r.name or r.email) for r in users_rows}

    activities_q = select(Activity.id, Activity.name, Activity.start_time).where(
        Activity.id.in_(activity_ids)
    )
    activities_rows = (await db.execute(activities_q)).all()
    activity_map = {r.id: (r.name, r.start_time) for r in activities_rows}

    results = []
    for e in efforts:
        act_name, act_start = activity_map.get(e.activity_id, (None, None))
        results.append(SegmentEffortResponse(
            id=e.id,
            segment_id=e.segment_id,
            activity_id=e.activity_id,
            user_id=e.user_id,
            user_name=user_map.get(e.user_id),
            activity_name=act_name,
            activity_start_time=act_start,
            elapsed_time_s=e.elapsed_time_s,
            avg_speed=e.avg_speed,
            avg_hr=e.avg_hr,
            avg_power=e.avg_power,
            start_time=e.start_time,
            created_at=e.created_at,
        ))
    return results


@router.get("/{segment_id}/pr", response_model=SegmentPRResponse)
async def get_segment_pr(
    segment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    seg = (await db.execute(
        select(Segment.id).where(Segment.id == segment_id)
    )).scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")

    q = (
        select(SegmentEffort)
        .where(
            SegmentEffort.segment_id == segment_id,
            SegmentEffort.user_id == user.id,
        )
        .order_by(SegmentEffort.elapsed_time_s.asc())
        .limit(1)
    )
    effort = (await db.execute(q)).scalar_one_or_none()
    if not effort:
        return SegmentPRResponse()

    return SegmentPRResponse(
        id=effort.id,
        elapsed_time_s=effort.elapsed_time_s,
        avg_speed=effort.avg_speed,
        avg_hr=effort.avg_hr,
        avg_power=effort.avg_power,
        start_time=effort.start_time,
        activity_id=effort.activity_id,
    )


@router.get("/{segment_id}/leaderboard", response_model=list[SegmentLeaderboardEntry])
async def get_segment_leaderboard(
    segment_id: int,
    limit: int = Query(10, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    seg = (await db.execute(
        select(Segment.id).where(Segment.id == segment_id)
    )).scalar_one_or_none()
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")

    best_q = (
        select(
            SegmentEffort.user_id,
            func.min(SegmentEffort.elapsed_time_s).label("best_time"),
        )
        .where(SegmentEffort.segment_id == segment_id)
        .group_by(SegmentEffort.user_id)
        .order_by(func.min(SegmentEffort.elapsed_time_s).asc())
        .limit(limit)
    )
    best_rows = (await db.execute(best_q)).all()
    if not best_rows:
        return []

    user_ids = [r.user_id for r in best_rows]
    users_q = select(User.id, User.name, User.email).where(User.id.in_(user_ids))
    users_rows = (await db.execute(users_q)).all()
    user_map = {r.id: (r.name or r.email) for r in users_rows}

    results = []
    for rank, row in enumerate(best_rows, 1):
        effort_q = (
            select(SegmentEffort)
            .where(
                SegmentEffort.segment_id == segment_id,
                SegmentEffort.user_id == row.user_id,
                SegmentEffort.elapsed_time_s == row.best_time,
            )
            .limit(1)
        )
        effort = (await db.execute(effort_q)).scalar_one()
        results.append(SegmentLeaderboardEntry(
            rank=rank,
            user_name=user_map.get(row.user_id),
            elapsed_time_s=row.best_time,
            avg_speed=effort.avg_speed,
            activity_id=effort.activity_id,
            start_time=effort.start_time,
        ))
    return results


@router.delete("/{segment_id}/efforts/{effort_id}")
async def delete_segment_effort(
    segment_id: int,
    effort_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    effort = (await db.execute(
        select(SegmentEffort).where(
            SegmentEffort.id == effort_id,
            SegmentEffort.segment_id == segment_id,
        )
    )).scalar_one_or_none()
    if not effort:
        raise HTTPException(status_code=404, detail="Effort not found")
    if effort.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the effort owner can delete this effort")

    await db.delete(effort)
    await db.commit()
    return {"ok": True}
