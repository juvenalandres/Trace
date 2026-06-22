import asyncio
import datetime
import datetime as dt
import logging
import math
import signal
import sys
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Date, func, literal_column, select, update
from sqlalchemy.orm import selectinload
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from trace_app.auth import get_current_user
from trace_app.cache import get_stats_cache, invalidate_user_stats
from trace_app.config import settings
from trace_app.database import async_session, get_db
from trace_app.limiter import limiter
from trace_app.logging import request_id_var, user_id_var, setup_logging
from trace_app.models import Activity, ActivityStats, Gear, Lap, Route, SegmentEffort, User, UserZone
from trace_app.models.training_plan import TrainingPlan
from trace_app.models.training_session import TrainingSession
from trace_app.models.training_block import TrainingBlock
from trace_app.routers.auth import router as auth_router
from trace_app.routers.segments import router as segments_router

from trace_app.schemas.activity import (
    ActivityCreate,
    ActivityListResponse,
    ActivityResponse,
    ActivityStatsResponse,
    ActivitySummary,
    ActivityUpdate,
    LapResponse,
)
from trace_app.schemas.gear import GearCreate, GearResponse, GearUpdate
from trace_app.schemas.route import (
    RouteCreate,
    RouteElevationRequest,
    RouteElevationResponse,
    RoutePlanRequest,
    RoutePlanResponse,
    RouteResponse,
    RouteUpdate,
)
from trace_app.schemas.user import UserResponse, UserUpdate
from trace_app.schemas.user_zone import UserZoneCreate, UserZoneResponse, UserZoneUpdate
from trace_app.schemas.training import (
    TrainingBlockCreate,
    TrainingBlockResponse,
    TrainingBlockUpdate,
    TrainingPlanCreate,
    TrainingPlanResponse,
    TrainingPlanUpdate,
    TrainingSessionCreate,
    TrainingSessionResponse,
    TrainingSessionUpdate,
)
from trace_app.services.activity_processor import process_activity
from trace_app.services.eddington import get_unit_divisor, get_unit_label
from trace_app.services.fit_parser import FitResult, map_fit_sport, parse_fit
from trace_app.services.gpx_parser import parse_gpx
from trace_app.database import is_postgres

# Setup structured logging
setup_logging()
logger = logging.getLogger(__name__)

# Rate limiter
app = FastAPI(title="Trace", version="0.1.0")
app.state.limiter = limiter


@app.on_event("startup")
async def recompute_training_loads():
    """Recompute CTL/ATL/TSB for all users on startup to fix stale gap data."""
    import asyncio
    from trace_app.models.daily_training_load import DailyTrainingLoad
    from trace_app.models.user import User
    from trace_app.services.training_load import recompute_ctl_atl_tsb

    async def _run():
        await asyncio.sleep(2)  # Wait for DB to be ready
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(User.id, User.max_hr, User.resting_hr)
                )
                users = result.all()
                for user_id, max_hr, resting_hr in users:
                    has_load = (await db.execute(
                        select(DailyTrainingLoad.id)
                        .where(DailyTrainingLoad.user_id == user_id)
                        .limit(1)
                    )).scalar_one_or_none()
                    if has_load is not None:
                        await recompute_ctl_atl_tsb(db, user_id, datetime.date(2000, 1, 1), max_hr, resting_hr)
                        await db.commit()
                        logger.info(f"Recomputed CTL/ATL/TSB for user {user_id}")
        except Exception as e:
            logger.warning(f"Training load recomputation skipped: {e}")

    asyncio.create_task(_run())
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Graceful shutdown handler
def handle_shutdown(sig, frame):
    logger.info("Received shutdown signal", extra={"extra": {"signal": sig}})
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


def _year_expr(col):
    """Extract year from a datetime column — works for both SQLite and PostgreSQL."""
    if is_postgres:
        return func.extract("year", col)
    return func.strftime("%Y", col)


def _year_month_expr(col):
    """Extract YYYY-MM from a datetime column — works for both SQLite and PostgreSQL."""
    if is_postgres:
        return func.to_char(col, "YYYY-MM")
    return func.strftime("%Y-%m", col)


def _date_expr(col):
    """Extract date from a datetime column — works for both SQLite and PostgreSQL."""
    if is_postgres:
        return func.cast(col, Date)
    return func.date(col)


def _week_start_expr(col):
    """Return the Monday of the week for a datetime column — works for both SQLite and PostgreSQL."""
    if is_postgres:
        # PostgreSQL date_trunc('week') returns Sunday, so shift to Monday
        return func.date_trunc("week", col + literal_column("INTERVAL '1 day'")) - literal_column("INTERVAL '1 day'")
    # SQLite: weekday 1 = Monday, '-7 days' backs up to the Monday of the current week
    return func.date(col, "weekday 1", "-7 days")

# CORS
cors_origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request size limit middleware
MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    # Generate request ID
    req_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
    request_id_var.set(req_id)

    # Check request size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Request too large. Max size is {settings.max_upload_size_mb}MB"},
        )

    # Process request and measure duration
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 1)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https://*.openstreetmap.org https://*.arcgisonline.com https://*.basemaps.cartocdn.com https://*.opentopomap.org; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "frame-ancestors 'none';"
    )

    # Add request ID to response headers
    response.headers["X-Request-ID"] = req_id

    # Log request
    logger.info(
        f"{request.method} {request.url.path}",
        extra={
            "extra": {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "client": request.client.host if request.client else None,
            }
        },
    )

    return response


app.include_router(auth_router)
app.include_router(segments_router)


@app.get("/api/health")
async def health():
    db_status = "ok"
    try:
        async with async_session() as session:
            await session.execute(select(1))
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
    }


@app.get("/api/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@app.put("/api/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if data.name is not None:
        user.name = data.name
    if data.preferred_units is not None:
        user.preferred_units = data.preferred_units
    if data.weight_kg is not None:
        user.weight_kg = data.weight_kg
    if data.ftp_watts is not None:
        user.ftp_watts = data.ftp_watts
    if data.max_hr is not None:
        user.max_hr = data.max_hr
    if data.resting_hr is not None:
        user.resting_hr = data.resting_hr
    user.updated_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    return user


@app.get("/api/users", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can list users")
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@app.put("/api/users/{user_id}/admin", response_model=UserResponse)
async def set_user_admin(
    user_id: int,
    is_admin: bool = Form(...),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can manage user roles")
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot change your own admin status")

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.is_admin = is_admin
    target_user.updated_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    await db.refresh(target_user)
    return target_user


@app.post("/api/zones", response_model=UserZoneResponse)
async def create_zone(
    data: UserZoneCreate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    zone = UserZone(
        user_id=user.id,
        zone_type=data.zone_type,
        zone_1_min=data.zone_1_min,
        zone_1_max=data.zone_1_max,
        zone_2_min=data.zone_2_min,
        zone_2_max=data.zone_2_max,
        zone_3_min=data.zone_3_min,
        zone_3_max=data.zone_3_max,
        zone_4_min=data.zone_4_min,
        zone_4_max=data.zone_4_max,
        zone_5_min=data.zone_5_min,
        zone_5_max=data.zone_5_max,
        valid_from=data.valid_from,
    )
    db.add(zone)
    await db.commit()
    return zone


@app.get("/api/zones", response_model=list[UserZoneResponse])
async def list_zones(
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(UserZone).where(UserZone.user_id == user.id).order_by(UserZone.zone_type)
    )
    return result.scalars().all()


@app.put("/api/zones/{zone_id}", response_model=UserZoneResponse)
async def update_zone(
    zone_id: int,
    data: UserZoneUpdate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(UserZone).where(UserZone.id == zone_id, UserZone.user_id == user.id)
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    for field in [
        "zone_1_min", "zone_1_max", "zone_2_min", "zone_2_max",
        "zone_3_min", "zone_3_max", "zone_4_min", "zone_4_max",
        "zone_5_min", "zone_5_max",
    ]:
        val = getattr(data, field)
        if val is not None:
            setattr(zone, field, val)

    await db.commit()
    return zone


@app.delete("/api/zones/{zone_id}")
async def delete_zone(
    zone_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(UserZone).where(UserZone.id == zone_id, UserZone.user_id == user.id)
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    await db.delete(zone)
    await db.commit()
    return {"ok": True}
async def create_activity(
    data: ActivityCreate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    activity = Activity(
        user_id=user.id,
        name=data.name,
        sport_type=data.sport_type,
        start_time=data.start_time,
        timezone=data.timezone,
        notes=data.notes,
        rpe=data.rpe,
        source="manual",
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity, ["stats", "laps"])
    invalidate_user_stats(user.id)
    return activity


@app.post("/api/activities/upload", response_model=ActivityResponse)
async def upload_activity(
    file: UploadFile,
    gear_id: int | None = Form(None),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    content = await file.read()
    filename = (file.filename or "").lower()

    if filename.endswith(".fit"):
        fit_result: FitResult = parse_fit(content)
        points = fit_result.points
        if not points:
            raise HTTPException(status_code=400, detail="No track points found in FIT file")

        session = fit_result.session
        session_overrides = {
            "distance_m": session.total_distance,
            "duration_s": session.total_elapsed_time,
            "calories": session.total_calories,
            "avg_speed": session.avg_speed,
            "max_speed": session.max_speed,
            "avg_hr": session.avg_hr,
            "max_hr": session.max_hr,
        }
        result = process_activity(points, session_overrides)
        source = "fit"
        sport_type = map_fit_sport(session.sport)
        start_time = session.start_time or points[0].time
        ext = "fit"
    elif filename.endswith(".gpx"):
        points = parse_gpx(content)
        if not points:
            raise HTTPException(status_code=400, detail="No track points found in GPX")
        result = process_activity(points)
        source = "gpx"
        sport_type = "other"
        start_time = points[0].time
        ext = "gpx"
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload .gpx or .fit")

    storage_dir = Path(settings.storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    if gear_id is not None:
        gear_q = select(Gear).where(Gear.id == gear_id, Gear.user_id == user.id)
        gear = (await db.execute(gear_q)).scalar_one_or_none()
        if not gear:
            raise HTTPException(status_code=400, detail="Gear not found")

    activity = Activity(
        user_id=user.id,
        name=file.filename or "Untitled Activity",
        sport_type=sport_type,
        start_time=start_time or datetime.datetime.now(datetime.timezone.utc),
        source=source,
        gear_id=gear_id,
    )
    db.add(activity)
    await db.flush()

    file_path = storage_dir / f"{activity.id}.{ext}"
    file_path.write_bytes(content)
    activity.raw_file_path = str(file_path)

    stats = ActivityStats(
        activity_id=activity.id,
        distance_m=result["distance_m"],
        duration_s=result["duration_s"],
        moving_time_s=result["moving_time_s"],
        elevation_gain=result["elevation_gain"],
        elevation_loss=result["elevation_loss"],
        avg_speed=result["avg_speed"],
        max_speed=result["max_speed"],
        avg_hr=result["avg_hr"],
        max_hr=result["max_hr"],
        avg_power=result["avg_power"],
        max_power=result["max_power"],
        avg_cadence=result["avg_cadence"],
        calories=result["calories"],
        avg_temp=result["avg_temp"],
        polyline=result["polyline"],
        simplified_time_series=result["simplified_time_series"],
        elevation_profile=result["elevation_profile"],
        min_lat=result["min_lat"],
        max_lat=result["max_lat"],
        min_lng=result["min_lng"],
        max_lng=result["max_lng"],
    )
    db.add(stats)

    lap_responses = []
    for lap_data in result["laps"]:
        lap = Lap(
            activity_id=activity.id,
            lap_index=lap_data["lap_index"],
            distance_m=lap_data["distance_m"],
            duration_s=lap_data["duration_s"],
            avg_speed=lap_data["avg_speed"],
            max_speed=lap_data["max_speed"],
            avg_hr=lap_data["avg_hr"],
            max_hr=lap_data["max_hr"],
            avg_power=lap_data["avg_power"],
            max_power=lap_data["max_power"],
            avg_cadence=lap_data["avg_cadence"],
            calories=lap_data["calories"],
        )
        db.add(lap)
        await db.flush()
        lap_responses.append(LapResponse(
            id=lap.id,
            lap_index=lap.lap_index,
            distance_m=lap.distance_m,
            duration_s=lap.duration_s,
            avg_speed=lap.avg_speed,
            max_speed=lap.max_speed,
            avg_hr=lap.avg_hr,
            max_hr=lap.max_hr,
            avg_power=lap.avg_power,
            max_power=lap.max_power,
            avg_cadence=lap.avg_cadence,
            calories=lap.calories,
        ))

    now = datetime.datetime.now(datetime.timezone.utc)

    # Auto-link to planned training session
    activity_date = activity.start_time.date()
    match_q = (
        select(TrainingSession)
        .join(TrainingPlan, TrainingPlan.id == TrainingSession.plan_id)
        .where(
            TrainingPlan.user_id == user.id,
            TrainingSession.scheduled_date == activity_date,
            TrainingSession.activity_id.is_(None),
            TrainingSession.status == "planned",
        )
    )
    match_result = await db.execute(match_q)
    candidates = match_result.scalars().all()
    for candidate in candidates:
        if candidate.sport_type is None or candidate.sport_type == activity.sport_type:
            candidate.activity_id = activity.id
            candidate.status = "completed"
            break

    # Compute training load and update daily CTL/ATL/TSB
    from trace_app.services.training_load import compute_trimp, compute_training_load, update_daily_training_load, backfill_daily_loads
    
    session_load = None
    if stats.avg_hr and stats.duration_s:
        session_load = compute_trimp(stats.duration_s, stats.avg_hr, stats.max_hr, user.max_hr)
    
    if session_load is None and stats.duration_s:
        session_load = compute_training_load(stats.duration_s, stats.avg_speed)
    
    if session_load is not None:
        stats.training_load = session_load
        activity_date = activity.start_time.date()
        await update_daily_training_load(db, user, activity_date, session_load)
        # Backfill any gap days so CTL/ATL decay is reflected day-by-day
        await backfill_daily_loads(db, user.id, user.max_hr, user.resting_hr)

    # Match segment efforts
    if points and source != "manual":
        from trace_app.services.segment_matcher import match_segments_for_activity
        await match_segments_for_activity(
            db, points, activity.id, user.id, sport_type, activity.start_time
        )

    await db.commit()
    invalidate_user_stats(user.id)

    return ActivityResponse(
        id=activity.id,
        user_id=activity.user_id,
        name=activity.name,
        sport_type=activity.sport_type,
        start_time=activity.start_time,
        timezone=activity.timezone,
        source=activity.source,
        raw_file_path=activity.raw_file_path,
        notes=activity.notes,
        rpe=activity.rpe,
        created_at=now,
        updated_at=now,
        stats=ActivityStatsResponse(
            distance_m=stats.distance_m,
            duration_s=stats.duration_s,
            moving_time_s=stats.moving_time_s,
            elevation_gain=stats.elevation_gain,
            elevation_loss=stats.elevation_loss,
            avg_speed=stats.avg_speed,
            max_speed=stats.max_speed,
            avg_hr=stats.avg_hr,
            max_hr=stats.max_hr,
            avg_power=stats.avg_power,
            max_power=stats.max_power,
            avg_cadence=stats.avg_cadence,
            calories=stats.calories,
            avg_temp=stats.avg_temp,
            polyline=stats.polyline,
            simplified_time_series=stats.simplified_time_series,
            elevation_profile=stats.elevation_profile,
            min_lat=stats.min_lat,
            max_lat=stats.max_lat,
            min_lng=stats.min_lng,
            max_lng=stats.max_lng,
        ),
        laps=lap_responses,
    )


@app.get("/api/activities", response_model=ActivityListResponse)
async def list_activities(
    page: int = 1,
    page_size: int = Query(20, le=500),
    sport_type: str | None = None,
    source: str | None = None,
    gear_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    distance_min: float | None = None,
    distance_max: float | None = None,
    elevation_min: float | None = None,
    elevation_max: float | None = None,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    query = (
        select(Activity)
        .where(Activity.user_id == user.id)
        .order_by(Activity.start_time.desc())
        .options(selectinload(Activity.stats))
    )
    count_query = select(func.count(Activity.id)).where(Activity.user_id == user.id)

    if sport_type:
        query = query.where(Activity.sport_type == sport_type)
        count_query = count_query.where(Activity.sport_type == sport_type)
    if source:
        query = query.where(Activity.source == source)
        count_query = count_query.where(Activity.source == source)
    if gear_id is not None:
        query = query.where(Activity.gear_id == gear_id)
        count_query = count_query.where(Activity.gear_id == gear_id)
    if date_from:
        from datetime import datetime as dt, timezone
        start_dt = dt.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        query = query.where(Activity.start_time >= start_dt)
        count_query = count_query.where(Activity.start_time >= start_dt)
    if date_to:
        from datetime import datetime as dt, timezone, timedelta
        end_dt = (dt.fromisoformat(date_to) + timedelta(days=1)).replace(tzinfo=timezone.utc)
        query = query.where(Activity.start_time < end_dt)
        count_query = count_query.where(Activity.start_time < end_dt)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    activities = result.scalars().all()

    items = []
    for a in activities:
        dist = a.stats.distance_m if a.stats else None
        elev = a.stats.elevation_gain if a.stats else None

        if distance_min is not None and (dist is None or dist < distance_min):
            continue
        if distance_max is not None and (dist is None or dist > distance_max):
            continue
        if elevation_min is not None and (elev is None or elev < elevation_min):
            continue
        if elevation_max is not None and (elev is None or elev > elevation_max):
            continue

        items.append(ActivitySummary(
            id=a.id,
            name=a.name,
            sport_type=a.sport_type,
            start_time=a.start_time,
            distance_m=dist,
            duration_s=a.stats.duration_s if a.stats else None,
            elevation_gain=elev,
            avg_speed=a.stats.avg_speed if a.stats else None,
            avg_hr=a.stats.avg_hr if a.stats else None,
            max_hr=a.stats.max_hr if a.stats else None,
            calories=a.stats.calories if a.stats else None,
        ))

    return ActivityListResponse(items=items, total=total, page=page, page_size=page_size)


@app.get("/api/activities/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(Activity)
        .where(Activity.id == activity_id, Activity.user_id == user.id)
        .options(selectinload(Activity.stats), selectinload(Activity.laps))
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@app.put("/api/activities/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: int,
    data: ActivityUpdate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if data.name is not None:
        activity.name = data.name
    if data.sport_type is not None:
        activity.sport_type = data.sport_type
    if data.timezone is not None:
        activity.timezone = data.timezone
    if data.notes is not None:
        activity.notes = data.notes
    if data.rpe is not None:
        activity.rpe = data.rpe

    if "gear_id" in data.model_fields_set:
        if data.gear_id is not None:
            gear_q = select(Gear).where(Gear.id == data.gear_id, Gear.user_id == user.id)
            gear = (await db.execute(gear_q)).scalar_one_or_none()
            if not gear:
                raise HTTPException(status_code=400, detail="Gear not found")
        activity.gear_id = data.gear_id

    activity.updated_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    await db.refresh(activity, ["stats", "laps"])
    invalidate_user_stats(user.id)
    return activity


@app.delete("/api/activities/{activity_id}")
async def delete_activity(
    activity_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Delete segment efforts referencing this activity
    effort_q = select(SegmentEffort).where(SegmentEffort.activity_id == activity_id)
    efforts = (await db.execute(effort_q)).scalars().all()
    for e in efforts:
        await db.delete(e)

    # Unlink any training sessions linked to this activity
    session_q = select(TrainingSession).where(TrainingSession.activity_id == activity_id)
    session_result = await db.execute(session_q)
    for session in session_result.scalars().all():
        session.activity_id = None
        session.status = "planned"

    await db.delete(activity)
    await db.commit()
    invalidate_user_stats(user.id)
    return {"ok": True}


@app.post("/api/gear", response_model=GearResponse)
async def create_gear(
    data: GearCreate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    gear = Gear(
        user_id=user.id,
        name=data.name,
        gear_type=data.gear_type,
        brand=data.brand,
        model=data.model,
        notes=data.notes,
        maintenance_interval_km=data.maintenance_interval_km,
    )
    db.add(gear)
    await db.commit()
    return gear


@app.get("/api/gear", response_model=list[GearResponse])
async def list_gear(
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(Gear).where(Gear.user_id == user.id).order_by(Gear.name)
    )
    return result.scalars().all()


@app.get("/api/gear/stats")
async def gear_stats(
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    q = (
        select(
            Gear.id,
            Gear.name,
            Gear.gear_type,
            Gear.retired,
            Gear.maintenance_interval_km,
            Gear.last_service_date,
            Gear.last_service_distance_m,
            func.count(Activity.id).label("workout_count"),
            func.coalesce(func.sum(ActivityStats.distance_m), 0).label("total_distance_m"),
            func.coalesce(func.avg(ActivityStats.distance_m), 0).label("avg_distance_m"),
            func.coalesce(func.sum(ActivityStats.elevation_gain), 0).label("total_elevation_m"),
            func.coalesce(func.sum(ActivityStats.moving_time_s), 0).label("total_moving_time_s"),
            func.coalesce(func.avg(ActivityStats.avg_speed), 0).label("avg_speed"),
            func.coalesce(func.sum(ActivityStats.calories), 0).label("total_calories"),
        )
        .outerjoin(Activity, Activity.gear_id == Gear.id)
        .outerjoin(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(Gear.user_id == user.id)
        .group_by(Gear.id)
        .order_by(func.sum(ActivityStats.distance_m).desc())
    )
    rows = (await db.execute(q)).all()

    return [
        {
            "gear_id": r[0],
            "gear_name": r[1],
            "gear_type": r[2],
            "retired": r[3],
            "maintenance_interval_km": r[4],
            "last_service_date": r[5].isoformat() if r[5] else None,
            "last_service_distance_m": r[6],
            "workout_count": r[7],
            "total_distance_m": round(r[8], 1),
            "avg_distance_m": round(r[9], 1),
            "total_elevation_m": round(r[10], 1),
            "total_moving_time_s": round(r[11], 1),
            "avg_speed": round(r[12], 2),
            "total_calories": r[13],
        }
        for r in rows
    ]


@app.put("/api/gear/{gear_id}", response_model=GearResponse)
async def update_gear(
    gear_id: int,
    data: GearUpdate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(Gear).where(Gear.id == gear_id, Gear.user_id == user.id)
    )
    gear = result.scalar_one_or_none()
    if not gear:
        raise HTTPException(status_code=404, detail="Gear not found")

    if data.name is not None:
        gear.name = data.name
    if data.gear_type is not None:
        gear.gear_type = data.gear_type
    if data.brand is not None:
        gear.brand = data.brand
    if data.model is not None:
        gear.model = data.model
    if data.notes is not None:
        gear.notes = data.notes
    if data.maintenance_interval_km is not None:
        gear.maintenance_interval_km = data.maintenance_interval_km
    if data.retired is not None:
        gear.retired = data.retired
        if data.retired:
            gear.retired_at = datetime.datetime.now(datetime.timezone.utc)
    if data.last_service_date is not None:
        gear.last_service_date = data.last_service_date
    if data.last_service_distance_m is not None:
        gear.last_service_distance_m = data.last_service_distance_m

    await db.commit()
    return gear


@app.post("/api/gear/{gear_id}/service")
async def mark_serviced(
    gear_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(Gear).where(Gear.id == gear_id, Gear.user_id == user.id)
    )
    gear = result.scalar_one_or_none()
    if not gear:
        raise HTTPException(status_code=404, detail="Gear not found")

    dist_q = (
        select(func.coalesce(func.sum(ActivityStats.distance_m), 0))
        .join(Activity, Activity.id == ActivityStats.activity_id)
        .where(Activity.gear_id == gear_id, Activity.user_id == user.id)
    )
    total_dist = (await db.execute(dist_q)).scalar_one()

    gear.last_service_date = datetime.date.today()
    gear.last_service_distance_m = total_dist
    await db.commit()
    return gear


@app.delete("/api/gear/{gear_id}")
async def delete_gear(
    gear_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(Gear).where(Gear.id == gear_id, Gear.user_id == user.id)
    )
    gear = result.scalar_one_or_none()
    if not gear:
        raise HTTPException(status_code=404, detail="Gear not found")
    await db.delete(gear)
    await db.commit()
    return {"ok": True}


@app.get("/api/stats/dashboard")
async def dashboard(
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    cache = get_stats_cache()
    cache_key = f"{user.id}:dashboard"
    cached = cache.get(cache_key)
    if cached:
        return cached

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    week_start = today - datetime.timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    async def period_stats(start: datetime.date, end: datetime.date | None = None):
        q = select(
            func.coalesce(func.sum(ActivityStats.distance_m), 0),
            func.coalesce(func.sum(ActivityStats.duration_s), 0),
            func.coalesce(func.sum(ActivityStats.elevation_gain), 0),
            func.count(Activity.id),
        ).join(ActivityStats, ActivityStats.activity_id == Activity.id).where(
            Activity.user_id == user.id,
            Activity.start_time >= datetime.datetime.combine(start, datetime.time.min, tzinfo=datetime.timezone.utc),
        )
        if end:
            q = q.where(Activity.start_time < datetime.datetime.combine(end, datetime.time.min, tzinfo=datetime.timezone.utc))
        r = (await db.execute(q)).one()
        return {
            "distance_m": r[0],
            "duration_s": r[1],
            "elevation_gain": r[2],
            "activity_count": r[3],
        }

    # Previous periods for trend calculation
    prev_week_start = week_start - datetime.timedelta(days=7)
    prev_week_end = week_start

    # Previous month
    if month_start.month == 1:
        prev_month_start = month_start.replace(year=month_start.year - 1, month=12)
    else:
        prev_month_start = month_start.replace(month=month_start.month - 1)

    # Previous year
    prev_year_start = year_start.replace(year=year_start.year - 1)

    sport_q = (
        select(
            Activity.sport_type,
            func.coalesce(func.sum(ActivityStats.distance_m), 0),
            func.coalesce(func.sum(ActivityStats.duration_s), 0),
            func.count(Activity.id),
        )
        .join(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(Activity.user_id == user.id)
        .group_by(Activity.sport_type)
    )

    recent_q = (
        select(Activity)
        .where(Activity.user_id == user.id)
        .order_by(Activity.start_time.desc())
        .limit(10)
        .options(selectinload(Activity.stats))
    )

    week, month, year, all_time, prev_week, prev_month, prev_year, sport_result, recent_result = (
        await asyncio.gather(
            period_stats(week_start),
            period_stats(month_start),
            period_stats(year_start),
            period_stats(datetime.date(2000, 1, 1)),
            period_stats(prev_week_start, prev_week_end),
            period_stats(prev_month_start, month_start),
            period_stats(prev_year_start, year_start),
            db.execute(sport_q),
            db.execute(recent_q),
        )
    )

    sport_rows = sport_result.all()
    by_sport = [
        {"sport_type": r[0], "distance_m": r[1], "duration_s": r[2], "activity_count": r[3]}
        for r in sport_rows
    ]

    recent_rows = recent_result.scalars().all()
    recent = []
    for a in recent_rows:
        recent.append(ActivitySummary(
            id=a.id,
            name=a.name,
            sport_type=a.sport_type,
            start_time=a.start_time,
            distance_m=a.stats.distance_m if a.stats else None,
            duration_s=a.stats.duration_s if a.stats else None,
            elevation_gain=a.stats.elevation_gain if a.stats else None,
            avg_speed=a.stats.avg_speed if a.stats else None,
            avg_hr=a.stats.avg_hr if a.stats else None,
            max_hr=a.stats.max_hr if a.stats else None,
            calories=a.stats.calories if a.stats else None,
        ))

    result = {
        "week": week,
        "prev_week": prev_week,
        "month": month,
        "prev_month": prev_month,
        "year": year,
        "prev_year": prev_year,
        "all_time": all_time,
        "by_sport": by_sport,
        "recent": recent,
    }
    cache.set(cache_key, result)
    return result


@app.get("/api/stats/eddington")
async def eddington_stats(
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    cache = get_stats_cache()
    cache_key = f"{user.id}:eddington"
    cached = cache.get(cache_key)
    if cached:
        return cached

    units = user.preferred_units or "metric"
    divisor = get_unit_divisor(units)
    unit_label = get_unit_label(units)

    # Eddington number via SQL window function — avoids loading all distances into memory
    divisor_expr = divisor  # Python-side divisor, applied in SQL
    ordered_q = (
        select(
            (ActivityStats.distance_m / divisor_expr).label("d"),
            func.row_number().over(order_by=(ActivityStats.distance_m / divisor_expr).desc()).label("rn"),
        )
        .join(Activity, Activity.id == ActivityStats.activity_id)
        .where(Activity.user_id == user.id, ActivityStats.distance_m.isnot(None))
    )
    ordered_result = (await db.execute(ordered_q)).all()

    e = 0
    for d, rn in ordered_result:
        if d >= rn:
            e = int(rn)
        else:
            break

    next_e = e + 1
    qualified_q = (
        select(func.count(Activity.id))
        .join(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(Activity.user_id == user.id, ActivityStats.distance_m >= next_e * divisor)
    )
    qualified = (await db.execute(qualified_q)).scalar() or 0
    needed = max(0, next_e - qualified)

    max_val = int(ordered_result[0][0]) if ordered_result else 0
    chart_range = max(max_val, next_e + 5)
    distribution = []
    for threshold in range(1, chart_range + 1):
        count = sum(1 for d, _ in ordered_result if d >= threshold)
        distribution.append({"threshold": threshold, "count": count})

    qualifying_q = (
        select(Activity, ActivityStats)
        .join(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(
            Activity.user_id == user.id,
            ActivityStats.distance_m >= e * divisor,
        )
        .order_by(ActivityStats.distance_m.desc())
    )
    qualifying_rows = (await db.execute(qualifying_q)).all()
    qualifying_activities = [
        {
            "id": a.id,
            "name": a.name,
            "sport_type": a.sport_type,
            "start_time": a.start_time.isoformat(),
            "distance_m": round(s.distance_m, 1),
            "distance_converted": round(s.distance_m / divisor, 1),
        }
        for a, s in qualifying_rows
    ]

    result = {
        "eddington_number": e,
        "next_milestone": next_e,
        "activities_qualified_for_next": qualified,
        "activities_needed_for_next": needed,
        "unit_label": unit_label,
        "distribution": distribution,
        "qualifying_activities": qualifying_activities,
    }
    cache.set(cache_key, result)
    return result


@app.get("/api/stats/personal-records")
async def personal_records(
    sport_type: str | None = None,
    year: int | None = None,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    cache = get_stats_cache()
    cache_key = f"{user.id}:pr:{sport_type or ''}:{year or ''}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    async def best(col, asc=False):
        q = (
            select(Activity, ActivityStats)
            .join(ActivityStats, ActivityStats.activity_id == Activity.id)
            .where(Activity.user_id == user.id, col.isnot(None))
        )
        if sport_type:
            q = q.where(Activity.sport_type == sport_type)
        if year:
            start = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
            end = datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
            q = q.where(Activity.start_time >= start, Activity.start_time < end)
        q = q.order_by(col.asc() if asc else col.desc()).limit(1)
        r = (await db.execute(q)).first()
        if not r:
            return None
        a, s = r
        return {
            "activity_id": a.id,
            "name": a.name,
            "sport_type": a.sport_type,
            "start_time": a.start_time.isoformat(),
            "value": getattr(s, col.name),
        }

    (
        longest_distance,
        longest_duration,
        highest_elevation,
        fastest_speed,
        highest_hr,
        max_speed,
    ) = await asyncio.gather(
        best(ActivityStats.distance_m),
        best(ActivityStats.duration_s),
        best(ActivityStats.elevation_gain),
        best(ActivityStats.avg_speed),
        best(ActivityStats.avg_hr),
        best(ActivityStats.max_speed),
    )

    return {
        "longest_distance": longest_distance,
        "longest_duration": longest_duration,
        "highest_elevation": highest_elevation,
        "fastest_speed": fastest_speed,
        "highest_hr": highest_hr,
        "max_speed": max_speed,
    }
    cache.set(cache_key, result)
    return result


@app.get("/api/stats/heatmap")
async def heatmap(
    start_date: str | None = None,
    end_date: str | None = None,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    cache = get_stats_cache()
    cache_key = f"{user.id}:heatmap:{start_date or ''}:{end_date or ''}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    today = datetime.date.today()
    if end_date:
        end = datetime.date.fromisoformat(end_date)
    else:
        end = today
    if start_date:
        start = datetime.date.fromisoformat(start_date)
    else:
        start = end - datetime.timedelta(days=364)

    start_dt = datetime.datetime.combine(start, datetime.time.min, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime.combine(end + datetime.timedelta(days=1), datetime.time.min, tzinfo=datetime.timezone.utc)

    q = (
        select(
            _date_expr(Activity.start_time).label("day"),
            func.coalesce(func.sum(ActivityStats.distance_m), 0).label("distance_m"),
            func.coalesce(func.sum(ActivityStats.moving_time_s), 0).label("moving_time_s"),
            func.coalesce(func.sum(ActivityStats.calories), 0).label("calories"),
        )
        .join(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(
            Activity.user_id == user.id,
            Activity.start_time >= start_dt,
            Activity.start_time < end_dt,
        )
        .group_by("day")
        .order_by("day")
    )
    rows = (await db.execute(q)).all()

    result = [
        {
            "date": r[0],
            "distance_m": r[1],
            "moving_time_s": r[2],
            "calories": r[3],
        }
        for r in rows
    ]
    cache.set(cache_key, result)
    return result


@app.get("/api/stats/activity-routes")
async def activity_routes(
    sport_type: str | None = None,
    year: int | None = None,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    q = (
        select(Activity, ActivityStats)
        .join(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(Activity.user_id == user.id, ActivityStats.polyline.isnot(None))
    )
    if sport_type:
        q = q.where(Activity.sport_type == sport_type)
    if year:
        start = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
        q = q.where(Activity.start_time >= start, Activity.start_time < end)
    q = q.order_by(Activity.start_time.desc())

    rows = (await db.execute(q)).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "sport_type": a.sport_type,
            "start_time": a.start_time.isoformat(),
            "polyline": s.polyline,
            "distance_m": s.distance_m,
        }
        for a, s in rows
    ]


@app.get("/api/stats/available-years", response_model=list[int])
async def available_years(
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    q = (
        select(_year_expr(Activity.start_time).label("y"))
        .where(Activity.user_id == user.id)
        .group_by("y")
        .order_by("y")
    )
    rows = (await db.execute(q)).scalars().all()
    return [int(y) for y in rows if y]


@app.get("/api/stats/volume")
async def volume(
    year: int | None = None,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    cache = get_stats_cache()
    cache_key = f"{user.id}:volume:{year or ''}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if year:
        start = datetime.date(year, 1, 1)
        end = datetime.date(year + 1, 1, 1)
    else:
        start = datetime.date(2000, 1, 1)
        end = datetime.date(2100, 1, 1)

    start_dt = datetime.datetime.combine(start, datetime.time.min, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime.combine(end, datetime.time.min, tzinfo=datetime.timezone.utc)

    q = (
        select(
            _year_month_expr(Activity.start_time).label("month"),
            func.count(Activity.id).label("count"),
            func.coalesce(func.sum(ActivityStats.distance_m), 0).label("distance_m"),
            func.coalesce(func.sum(ActivityStats.duration_s), 0).label("duration_s"),
            func.coalesce(func.sum(ActivityStats.elevation_gain), 0).label("elevation_m"),
            func.coalesce(func.sum(ActivityStats.calories), 0).label("calories"),
        )
        .join(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(Activity.user_id == user.id, Activity.start_time >= start_dt, Activity.start_time < end_dt)
        .group_by("month")
        .order_by("month")
    )
    rows = (await db.execute(q)).all()

    sport_q = (
        select(
            Activity.sport_type,
            func.count(Activity.id).label("count"),
            func.coalesce(func.sum(ActivityStats.distance_m), 0).label("distance_m"),
            func.coalesce(func.sum(ActivityStats.duration_s), 0).label("duration_s"),
        )
        .join(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(Activity.user_id == user.id, Activity.start_time >= start_dt, Activity.start_time < end_dt)
        .group_by(Activity.sport_type)
        .order_by(func.sum(ActivityStats.distance_m).desc())
    )
    sport_rows = (await db.execute(sport_q)).all()

    result = {
        "monthly": [
            {
                "month": r[0],
                "count": r[1],
                "distance_m": round(r[2], 1),
                "duration_s": round(r[3], 1),
                "elevation_m": round(r[4], 1),
                "calories": r[5],
            }
            for r in rows
        ],
        "by_sport": [
            {
                "sport_type": r[0],
                "count": r[1],
                "distance_m": round(r[2], 1),
                "duration_s": round(r[3], 1),
            }
            for r in sport_rows
        ],
    }
    cache.set(cache_key, result)
    return result


# ── Training Plans ──────────────────────────────────────────────────


@app.post("/api/training/plans", response_model=TrainingPlanResponse)
async def create_plan(
    data: TrainingPlanCreate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    plan = TrainingPlan(
        user_id=user.id,
        name=data.name,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    db.add(plan)
    await db.commit()
    result = await db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan.id)
        .options(selectinload(TrainingPlan.sessions), selectinload(TrainingPlan.blocks).selectinload(TrainingBlock.sessions))
    )
    return result.scalar_one()


@app.get("/api/training/plans", response_model=list[TrainingPlanResponse])
async def list_plans(
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.user_id == user.id)
        .order_by(TrainingPlan.created_at.desc())
        .options(selectinload(TrainingPlan.sessions), selectinload(TrainingPlan.blocks).selectinload(TrainingBlock.sessions))
    )
    return result.scalars().all()


@app.get("/api/training/plans/{plan_id}", response_model=TrainingPlanResponse)
async def get_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan_id, TrainingPlan.user_id == user.id)
        .options(selectinload(TrainingPlan.sessions), selectinload(TrainingPlan.blocks).selectinload(TrainingBlock.sessions))
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@app.put("/api/training/plans/{plan_id}", response_model=TrainingPlanResponse)
async def update_plan(
    plan_id: int,
    data: TrainingPlanUpdate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan_id, TrainingPlan.user_id == user.id)
        .options(selectinload(TrainingPlan.sessions), selectinload(TrainingPlan.blocks).selectinload(TrainingBlock.sessions))
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if data.name is not None:
        plan.name = data.name
    if data.description is not None:
        plan.description = data.description
    if data.start_date is not None:
        plan.start_date = data.start_date
    if data.end_date is not None:
        plan.end_date = data.end_date

    await db.commit()
    result = await db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan.id)
        .options(selectinload(TrainingPlan.sessions), selectinload(TrainingPlan.blocks).selectinload(TrainingBlock.sessions))
    )
    return result.scalar_one()


@app.delete("/api/training/plans/{plan_id}")
async def delete_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id, TrainingPlan.user_id == user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await db.delete(plan)
    await db.commit()
    return {"ok": True}


# ── Training Sessions ───────────────────────────────────────────────


@app.post("/api/training/plans/{plan_id}/sessions", response_model=TrainingSessionResponse)
async def create_session(
    plan_id: int,
    data: TrainingSessionCreate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    plan_result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id, TrainingPlan.user_id == user.id)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    targets_json = [t.model_dump() for t in data.targets] if data.targets else None
    session = TrainingSession(
        plan_id=plan_id,
        scheduled_date=data.scheduled_date,
        sport_type=data.sport_type,
        name=data.name,
        description=data.description,
        targets=targets_json,
        intervals=data.intervals,
        notes=data.notes,
        rest_day=data.rest_day,
        block_id=data.block_id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@app.put("/api/training/sessions/{session_id}", response_model=TrainingSessionResponse)
async def update_session(
    session_id: int,
    data: TrainingSessionUpdate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(TrainingSession)
        .join(TrainingPlan, TrainingPlan.id == TrainingSession.plan_id)
        .where(TrainingSession.id == session_id, TrainingPlan.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if data.scheduled_date is not None:
        session.scheduled_date = data.scheduled_date
    if data.sport_type is not None:
        session.sport_type = data.sport_type
    if data.name is not None:
        session.name = data.name
    if data.description is not None:
        session.description = data.description
    if data.targets is not None:
        session.targets = [t.model_dump() for t in data.targets] if data.targets else None
    if data.intervals is not None:
        session.intervals = data.intervals
    if data.notes is not None:
        session.notes = data.notes
    if data.rest_day is not None:
        session.rest_day = data.rest_day
    if data.block_id is not None:
        session.block_id = data.block_id
    if data.status is not None:
        session.status = data.status

    await db.commit()
    await db.refresh(session)
    return session


@app.delete("/api/training/sessions/{session_id}")
async def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(TrainingSession)
        .join(TrainingPlan, TrainingPlan.id == TrainingSession.plan_id)
        .where(TrainingSession.id == session_id, TrainingPlan.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()
    return {"ok": True}


# ── Training Blocks ───────────────────────────────────────────────


@app.post("/api/training/plans/{plan_id}/blocks", response_model=TrainingBlockResponse)
async def create_block(
    plan_id: int,
    data: TrainingBlockCreate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    plan_result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id, TrainingPlan.user_id == user.id)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if data.sort_order is None:
        result = await db.execute(
            select(func.max(TrainingBlock.sort_order))
            .where(TrainingBlock.plan_id == plan_id)
        )
        max_order = result.scalar()
        sort_order = (max_order or 0) + 1
    else:
        sort_order = data.sort_order

    block = TrainingBlock(
        plan_id=plan_id,
        name=data.name,
        description=data.description,
        focus=data.focus,
        block_type=data.block_type or "general",
        sort_order=sort_order,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    db.add(block)
    await db.commit()
    result = await db.execute(
        select(TrainingBlock)
        .where(TrainingBlock.id == block.id)
        .options(selectinload(TrainingBlock.sessions))
    )
    return result.scalar_one()


@app.get("/api/training/plans/{plan_id}/blocks", response_model=list[TrainingBlockResponse])
async def list_blocks(
    plan_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    plan_result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id, TrainingPlan.user_id == user.id)
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Plan not found")

    result = await db.execute(
        select(TrainingBlock)
        .where(TrainingBlock.plan_id == plan_id)
        .order_by(TrainingBlock.sort_order)
        .options(selectinload(TrainingBlock.sessions))
    )
    return result.scalars().all()


@app.get("/api/training/blocks/{block_id}", response_model=TrainingBlockResponse)
async def get_block(
    block_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(TrainingBlock)
        .join(TrainingPlan, TrainingPlan.id == TrainingBlock.plan_id)
        .where(TrainingBlock.id == block_id, TrainingPlan.user_id == user.id)
        .options(selectinload(TrainingBlock.sessions))
    )
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    return block


@app.put("/api/training/blocks/{block_id}", response_model=TrainingBlockResponse)
async def update_block(
    block_id: int,
    data: TrainingBlockUpdate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(TrainingBlock)
        .join(TrainingPlan, TrainingPlan.id == TrainingBlock.plan_id)
        .where(TrainingBlock.id == block_id, TrainingPlan.user_id == user.id)
        .options(selectinload(TrainingBlock.sessions))
    )
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    if data.name is not None:
        block.name = data.name
    if data.description is not None:
        block.description = data.description
    if data.focus is not None:
        block.focus = data.focus
    if data.block_type is not None:
        block.block_type = data.block_type
    if data.sort_order is not None:
        block.sort_order = data.sort_order
    if data.start_date is not None:
        block.start_date = data.start_date
    if data.end_date is not None:
        block.end_date = data.end_date

    await db.commit()
    result = await db.execute(
        select(TrainingBlock)
        .where(TrainingBlock.id == block.id)
        .options(selectinload(TrainingBlock.sessions))
    )
    return result.scalar_one()


@app.delete("/api/training/blocks/{block_id}")
async def delete_block(
    block_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(TrainingBlock)
        .join(TrainingPlan, TrainingPlan.id == TrainingBlock.plan_id)
        .where(TrainingBlock.id == block_id, TrainingPlan.user_id == user.id)
    )
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    # Unlink sessions before deleting block (block_id FK has ON DELETE SET NULL)
    await db.execute(
        update(TrainingSession)
        .where(TrainingSession.block_id == block_id)
        .values(block_id=None)
    )
    await db.delete(block)
    await db.commit()
    return {"ok": True}


# ── Training Insights ──────────────────────────────────────────────


@app.get("/api/training/insights")
async def training_insights(
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    weeks_back = 24
    start_date = start_of_week - timedelta(weeks=weeks_back - 1)
    start_dt = datetime.datetime.combine(start_date, datetime.time.min).replace(tzinfo=datetime.timezone.utc)

    # Weekly volume aggregated in SQL
    week_q = (
        select(
            _week_start_expr(Activity.start_time).label("week_start"),
            func.coalesce(func.sum(ActivityStats.distance_m), 0).label("distance_m"),
            func.coalesce(func.sum(ActivityStats.duration_s), 0).label("duration_s"),
            func.coalesce(func.sum(ActivityStats.moving_time_s), 0).label("moving_time_s"),
            func.count(Activity.id).label("count"),
        )
        .join(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(
            Activity.user_id == user.id,
            Activity.start_time >= start_dt,
        )
        .group_by("week_start")
        .order_by("week_start")
    )
    week_rows = (await db.execute(week_q)).all()

    # Sport pace trends aggregated in SQL
    pace_q = (
        select(
            _week_start_expr(Activity.start_time).label("week_start"),
            Activity.sport_type,
            func.avg(ActivityStats.avg_speed).label("avg_speed"),
        )
        .join(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(
            Activity.user_id == user.id,
            Activity.start_time >= start_dt,
            ActivityStats.avg_speed.isnot(None),
            ActivityStats.avg_speed > 0,
        )
        .group_by("week_start", Activity.sport_type)
        .order_by("week_start")
    )
    pace_rows = (await db.execute(pace_q)).all()

    # Build weekly buckets (all weeks, even empty)
    weekly: dict[str, dict] = {}
    for i in range(weeks_back):
        wk = start_date + timedelta(weeks=i)
        key = wk.isoformat()
        weekly[key] = {"week_start": key, "distance_m": 0, "duration_s": 0, "moving_time_s": 0, "count": 0}

    # Fill from SQL aggregation
    for row in week_rows:
        key = str(row.week_start) if isinstance(row.week_start, date) else row.week_start
        if key in weekly:
            weekly[key]["distance_m"] = round(row.distance_m or 0, 1)
            weekly[key]["duration_s"] = round(row.duration_s or 0, 1)
            weekly[key]["moving_time_s"] = round(row.moving_time_s or 0, 1)
            weekly[key]["count"] = row.count

    # Build pace trends from SQL aggregation
    pace_data: dict[str, dict[str, float]] = {}
    for row in pace_rows:
        key = str(row.week_start) if isinstance(row.week_start, date) else row.week_start
        sport = row.sport_type or "other"
        if sport not in pace_data:
            pace_data[sport] = {}
        pace_data[sport][key] = round(row.avg_speed, 2) if row.avg_speed else None

    pace_trends: dict[str, list[dict]] = {}
    for sport, weeks in pace_data.items():
        trend = []
        for i in range(weeks_back):
            wk = start_date + timedelta(weeks=i)
            key = wk.isoformat()
            trend.append({"week_start": key, "avg_speed": weeks.get(key)})
        pace_trends[sport] = trend

    # Consistency streak (consecutive weeks with ≥1 activity, ending at current week)
    weekly_list = sorted(weekly.values(), key=lambda w: w["week_start"], reverse=True)
    streak = 0
    for wk in weekly_list:
        if wk["count"] > 0:
            streak += 1
        else:
            break

    return {
        "weekly_volume": sorted(weekly_list, key=lambda w: w["week_start"]),
        "pace_trends": pace_trends,
        "consistency_streak": streak,
        "total_weeks": weeks_back,
    }


@app.get("/api/training/weekly-volume")
async def training_weekly_volume(
    plan_id: int,
    weeks: int = Query(24, le=104),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Return weekly planned vs actual volume per sport for a plan."""
    # Verify plan ownership
    plan_result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.id == plan_id, TrainingPlan.user_id == user.id)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    start_date = start_of_week - timedelta(weeks=weeks - 1)

    # Get all sessions for this plan in range
    sessions_q = (
        select(TrainingSession)
        .where(
            TrainingSession.plan_id == plan_id,
            TrainingSession.scheduled_date >= start_date,
            TrainingSession.rest_day == False,
        )
        .order_by(TrainingSession.scheduled_date)
    )
    sessions = (await db.execute(sessions_q)).scalars().all()

    # Get all activities in range for this user
    act_q = (
        select(
            Activity.start_time,
            Activity.sport_type,
            ActivityStats.distance_m,
            ActivityStats.duration_s,
        )
        .join(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(
            Activity.user_id == user.id,
            Activity.start_time >= datetime.datetime.combine(start_date, datetime.time.min).replace(tzinfo=datetime.timezone.utc),
        )
        .order_by(Activity.start_time)
    )
    activities = (await db.execute(act_q)).all()

    # Build weekly buckets
    weekly: dict[str, dict] = {}
    for i in range(weeks):
        wk = start_date + timedelta(weeks=i)
        key = wk.isoformat()
        weekly[key] = {
            "week_start": key,
            "planned": {},
            "actual": {},
            "total_planned_distance_m": 0,
            "total_planned_duration_s": 0,
            "total_planned_count": 0,
            "total_actual_distance_m": 0,
            "total_actual_duration_s": 0,
            "total_actual_count": 0,
        }

    # Aggregate planned volume from session targets
    for session in sessions:
        week_start = session.scheduled_date - timedelta(days=session.scheduled_date.weekday())
        key = week_start.isoformat()
        if key not in weekly:
            continue

        sport = session.sport_type or "other"
        if sport not in weekly[key]["planned"]:
            weekly[key]["planned"][sport] = {"distance_m": 0, "duration_s": 0, "count": 0}

        weekly[key]["planned"][sport]["count"] += 1
        weekly[key]["total_planned_count"] += 1

        if session.targets:
            for target in session.targets:
                t_type = target.get("type")
                t_value = target.get("value")
                if t_type == "distance" and t_value:
                    unit = target.get("unit", "km")
                    dist_m = t_value * 1000 if unit == "km" else t_value * 1609.34 if unit == "mi" else t_value
                    weekly[key]["planned"][sport]["distance_m"] += dist_m
                    weekly[key]["total_planned_distance_m"] += dist_m
                elif t_type == "duration" and t_value:
                    unit = target.get("unit", "h")
                    dur_s = t_value * 3600 if unit == "h" else t_value * 60 if unit == "min" else t_value
                    weekly[key]["planned"][sport]["duration_s"] += dur_s
                    weekly[key]["total_planned_duration_s"] += dur_s

    # Aggregate actual volume from activities
    for row in activities:
        act_date = row[0].date() if hasattr(row[0], 'date') else row[0]
        week_start = act_date - timedelta(days=act_date.weekday())
        key = week_start.isoformat()
        if key not in weekly:
            continue

        sport = row[1] or "other"
        if sport not in weekly[key]["actual"]:
            weekly[key]["actual"][sport] = {"distance_m": 0, "duration_s": 0, "count": 0}

        weekly[key]["actual"][sport]["count"] += 1
        weekly[key]["actual"][sport]["distance_m"] += row[2] or 0
        weekly[key]["actual"][sport]["duration_s"] += row[3] or 0
        weekly[key]["total_actual_count"] += 1
        weekly[key]["total_actual_distance_m"] += row[2] or 0
        weekly[key]["total_actual_duration_s"] += row[3] or 0

    # Round values
    weekly_list = sorted(weekly.values(), key=lambda w: w["week_start"])
    for wk in weekly_list:
        for sport_data in [*wk["planned"].values(), *wk["actual"].values()]:
            sport_data["distance_m"] = round(sport_data["distance_m"], 1)
            sport_data["duration_s"] = round(sport_data["duration_s"], 1)
        wk["total_planned_distance_m"] = round(wk["total_planned_distance_m"], 1)
        wk["total_planned_duration_s"] = round(wk["total_planned_duration_s"], 1)
        wk["total_actual_distance_m"] = round(wk["total_actual_distance_m"], 1)
        wk["total_actual_duration_s"] = round(wk["total_actual_duration_s"], 1)

    return {
        "plan_id": plan_id,
        "weeks": weekly_list,
    }


@app.get("/api/training/ctl")
async def training_ctl(
    days: int = Query(90, le=365),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Return CTL (Fitness), ATL (Fatigue), TSB (Form), ACWR for the last N days."""
    from trace_app.models.daily_training_load import DailyTrainingLoad
    from trace_app.services.training_load import backfill_daily_loads, compute_acwr, acwr_status

    # Backfill zero-load days up to yesterday so decay is reflected in real time
    await backfill_daily_loads(db, user.id, user.max_hr, user.resting_hr)

    today = date.today()
    start_date = today - timedelta(days=days)

    # CTL/ATL decay constants (same as in recompute_ctl_atl_tsb)
    ctl_decay = 1 - math.exp(-1 / 42)
    atl_decay = 1 - math.exp(-1 / 7)

    # Load all records into a dict for O(1) lookup — avoids day-by-day iteration
    result = await db.execute(
        select(DailyTrainingLoad)
        .where(
            DailyTrainingLoad.user_id == user.id,
            DailyTrainingLoad.date >= start_date,
        )
        .order_by(DailyTrainingLoad.date)
    )
    records = {r.date: r for r in result.scalars().all()}

    # Build daily data via date range iteration (minimal, no nested DB calls)
    daily_data = []
    load_history = []
    prev_ctl = 0.0
    prev_atl = 0.0

    for day_offset in range(days + 1):
        current_date = start_date + timedelta(days=day_offset)
        rec = records.get(current_date)
        if rec:
            load_history.append(rec.training_load)
            prev_ctl = rec.ctl
            prev_atl = rec.atl
            daily_data.append({
                "date": current_date.isoformat(),
                "training_load": round(rec.training_load, 1),
                "ctl": round(prev_ctl, 1),
                "atl": round(prev_atl, 1),
                "tsb": round(rec.tsb, 1),
            })
        else:
            load_history.append(0.0)
            prev_ctl = prev_ctl + (0 - prev_ctl) * ctl_decay
            prev_atl = prev_atl + (0 - prev_atl) * atl_decay
            daily_data.append({
                "date": current_date.isoformat(),
                "training_load": 0.0,
                "ctl": round(prev_ctl, 1),
                "atl": round(prev_atl, 1),
                "tsb": round(prev_ctl - prev_atl, 1),
            })

    # Compute ACWR for the latest day
    acwr_value = compute_acwr(load_history)
    acwr_info = None
    if acwr_value is not None:
        status_info = acwr_status(acwr_value)
        acwr_info = {
            "value": acwr_value,
            "acute_load": round(sum(load_history[-7:]), 1),
            "chronic_load": round(sum(load_history[-28:]) / 4, 1) if len(load_history) >= 28 else None,
            **status_info,
        }

    # Get sport-specific load distribution
    sport_load_q = (
        select(
            Activity.sport_type,
            func.sum(ActivityStats.training_load).label("total_load"),
            func.count(Activity.id).label("count"),
        )
        .join(ActivityStats, ActivityStats.activity_id == Activity.id)
        .where(
            Activity.user_id == user.id,
            Activity.start_time >= datetime.datetime.combine(start_date, datetime.time.min).replace(tzinfo=datetime.timezone.utc),
            ActivityStats.training_load.isnot(None),
        )
        .group_by(Activity.sport_type)
    )
    sport_rows = (await db.execute(sport_load_q)).all()
    sport_load = [
        {"sport_type": r[0] or "other", "total_load": round(r[1] or 0, 1), "count": r[2]}
        for r in sport_rows
    ]

    # Get weekly load for ACWR trend (last 12 weeks)
    weekly_loads = []
    for i in range(min(12, len(load_history) // 7)):
        week_start_idx = len(load_history) - (i + 1) * 7
        week_end_idx = len(load_history) - i * 7
        if week_start_idx >= 0:
            week_sum = sum(load_history[week_start_idx:week_end_idx])
            week_date = today - timedelta(weeks=i)
            weekly_loads.append({
                "week_start": (week_date - timedelta(days=week_date.weekday())).isoformat(),
                "load": round(week_sum, 1),
            })
    weekly_loads.reverse()

    return {
        "days": days,
        "data": daily_data,
        "acwr": acwr_info,
        "sport_load": sport_load,
        "weekly_loads": weekly_loads,
    }


# ── Route Planner ──────────────────────────────────────────────────────────────

OSRM_BASE_URL = "https://router.project-osrm.org"
OPEN_METEO_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"


@app.post("/api/routes/plan", response_model=RoutePlanResponse)
async def plan_route(
    data: RoutePlanRequest,
    user: User = Depends(get_current_user),
):
    if len(data.waypoints) < 2:
        raise HTTPException(status_code=400, detail="At least 2 waypoints required")

    coords = ";".join(f"{w.lng},{w.lat}" for w in data.waypoints)
    url = f"{OSRM_BASE_URL}/route/v1/foot/{coords}?overview=full&geometries=polyline"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Routing service error: {e}")

    if result.get("code") != "Ok" or not result.get("routes"):
        raise HTTPException(status_code=422, detail="No route found for the given waypoints")

    route = result["routes"][0]
    return RoutePlanResponse(
        polyline=route["geometry"],
        distance_m=route["distance"],
        waypoints=data.waypoints,
    )


@app.post("/api/routes/elevation", response_model=RouteElevationResponse)
async def get_elevation(
    data: RouteElevationRequest,
    user: User = Depends(get_current_user),
):
    if not data.points:
        raise HTTPException(status_code=400, detail="No points provided")

    points = data.points[:100]
    lats = ",".join(f"{p.lat}" for p in points)
    lngs = ",".join(f"{p.lng}" for p in points)
    url = f"{OPEN_METEO_ELEVATION_URL}?latitude={lats}&longitude={lngs}"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Elevation service error: {e}")

    elevations = result.get("elevation", [])
    if len(elevations) != len(points):
        raise HTTPException(status_code=502, detail="Elevation data mismatch")

    profile = []
    cumulative_distance = 0.0
    gain = 0.0
    loss = 0.0

    for i, (pt, ele) in enumerate(zip(points, elevations)):
        if i > 0:
            prev = points[i - 1]
            dlat = math.radians(pt.lat - prev.lat)
            dlng = math.radians(pt.lng - prev.lng)
            a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(prev.lat)) * math.cos(math.radians(pt.lat)) * math.sin(dlng / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            cumulative_distance += 6371000 * c

        profile.append({"distance": round(cumulative_distance, 1), "elevation": round(ele, 1)})

        if i > 0:
            diff = ele - elevations[i - 1]
            if diff > 0:
                gain += diff
            else:
                loss += abs(diff)

    return RouteElevationResponse(
        elevation_profile=profile,
        elevation_gain_m=round(gain, 1),
        elevation_loss_m=round(loss, 1),
    )


@app.get("/api/routes", response_model=list[RouteResponse])
async def list_routes(
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(Route).where(Route.user_id == user.id).order_by(Route.created_at.desc())
    )
    return result.scalars().all()


@app.get("/api/routes/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(Route).where(Route.id == route_id, Route.user_id == user.id)
    )
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@app.post("/api/routes", response_model=RouteResponse)
async def create_route(
    data: RouteCreate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    route = Route(
        user_id=user.id,
        name=data.name,
        description=data.description,
        waypoints=[w.model_dump() for w in data.waypoints],
        route_polyline=data.route_polyline,
        distance_m=data.distance_m,
        elevation_gain_m=data.elevation_gain_m,
        elevation_loss_m=data.elevation_loss_m,
        elevation_profile=[p.model_dump() for p in data.elevation_profile] if data.elevation_profile else None,
        sport_type=data.sport_type,
    )
    db.add(route)
    await db.commit()
    await db.refresh(route)
    return route


@app.put("/api/routes/{route_id}", response_model=RouteResponse)
async def update_route(
    route_id: int,
    data: RouteUpdate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(Route).where(Route.id == route_id, Route.user_id == user.id)
    )
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    update_data = data.model_dump(exclude_unset=True)
    if "waypoints" in update_data and update_data["waypoints"] is not None:
        update_data["waypoints"] = [w.model_dump() if hasattr(w, "model_dump") else w for w in update_data["waypoints"]]
    if "elevation_profile" in update_data and update_data["elevation_profile"] is not None:
        update_data["elevation_profile"] = [p.model_dump() if hasattr(p, "model_dump") else p for p in update_data["elevation_profile"]]

    for key, value in update_data.items():
        setattr(route, key, value)

    await db.commit()
    await db.refresh(route)
    return route


@app.delete("/api/routes/{route_id}")
async def delete_route(
    route_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db.execute(
        select(Route).where(Route.id == route_id, Route.user_id == user.id)
    )
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    await db.delete(route)
    await db.commit()
    return {"ok": True}


# --- Static file serving for production frontend ---
class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        # Vite hashes asset filenames — safe to cache aggressively
        if path and ("-" in path or "." in path):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


static_dir = Path(__file__).parent.parent / "static"
if static_dir.is_dir():
    app.mount("/assets", CachedStaticFiles(directory=str(static_dir / "assets")), name="static-assets")

    @app.get("/")
    async def serve_root():
        return FileResponse(static_dir / "index.html")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")
