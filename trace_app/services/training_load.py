import math
import datetime
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from trace_app.models.activity import Activity
from trace_app.models.activity_stats import ActivityStats
from trace_app.models.daily_training_load import DailyTrainingLoad
from trace_app.models.user import User


def compute_trimp(
    duration_s: float,
    avg_hr: float | None,
    max_hr: int | None,
    resting_hr: int | None,
) -> float | None:
    """Compute TRIMP (Training Impulse) using the Banister formula.
    
    TRIMP = duration_min * (%HRmax) * e^(1.92 * %HRmax)
    
    Where %HRmax = (avg_hr - resting_hr) / (max_hr - resting_hr)
    
    Returns None if HR data is insufficient.
    """
    if not avg_hr or not max_hr or not resting_hr:
        return None
    if max_hr <= resting_hr:
        return None

    duration_min = duration_s / 60.0
    hr_reserve = max_hr - resting_hr
    hr_ratio = (avg_hr - resting_hr) / hr_reserve
    
    # Clamp to valid range
    hr_ratio = max(0.0, min(1.0, hr_ratio))
    
    # Banister TRIMP formula
    trimp = duration_min * hr_ratio * 0.64 * math.exp(1.92 * hr_ratio)
    return round(trimp, 1)


def compute_training_load(duration_s: float, avg_speed: float | None) -> float | None:
    """Fallback training load based on duration and intensity.
    
    If HR data is not available, use a simpler formula based on duration and speed.
    """
    if not duration_s:
        return None
    
    duration_min = duration_s / 60.0
    
    if avg_speed and avg_speed > 0:
        # Simple intensity factor based on speed (m/s)
        # Typical speeds: walking 1.4, running 3.0, cycling 8.0 m/s
        intensity = min(avg_speed / 5.0, 2.0)  # Normalize to ~1.0 for running pace
        return round(duration_min * intensity, 1)
    
    # Just use duration as load
    return round(duration_min, 1)


async def update_daily_training_load(
    db: AsyncSession,
    user: User,
    activity_date: date,
    session_load: float,
) -> None:
    """Update or insert daily training load and recompute CTL/ATL/TSB from that date forward."""
    
    # Get or create daily record
    result = await db.execute(
        select(DailyTrainingLoad).where(
            DailyTrainingLoad.user_id == user.id,
            DailyTrainingLoad.date == activity_date,
        )
    )
    daily = result.scalar_one_or_none()
    
    if daily:
        daily.training_load += session_load
    else:
        daily = DailyTrainingLoad(
            user_id=user.id,
            date=activity_date,
            training_load=session_load,
        )
        db.add(daily)
    
    await db.flush()
    
    # Recompute CTL/ATL/TSB from this date forward
    await recompute_ctl_atl_tsb(db, user.id, activity_date, user.max_hr, user.resting_hr)


async def recompute_ctl_atl_tsb(
    db: AsyncSession,
    user_id: int,
    from_date: date,
    max_hr: int | None,
    resting_hr: int | None,
) -> None:
    """Recompute CTL/ATL/TSB from a given date forward.

    Handles gaps in daily records by decaying CTL/ATL across missing days.
    """

    # CTL decay constant (42-day half-life)
    ctl_decay = 1 - math.exp(-1 / 42)
    # ATL decay constant (7-day half-life)
    atl_decay = 1 - math.exp(-1 / 7)

    # Get all daily records for this user, ordered by date
    result = await db.execute(
        select(DailyTrainingLoad)
        .where(DailyTrainingLoad.user_id == user_id)
        .order_by(DailyTrainingLoad.date)
    )
    all_days = result.scalars().all()

    if not all_days:
        return

    # Find the index of the from_date
    start_idx = 0
    for i, day in enumerate(all_days):
        if day.date >= from_date:
            start_idx = i
            break

    # Get the CTL/ATL values from the day before from_date
    prev_ctl = 0.0
    prev_atl = 0.0
    prev_date: date | None = None

    if start_idx > 0:
        prev_day = all_days[start_idx - 1]
        prev_ctl = prev_day.ctl
        prev_atl = prev_day.atl
        prev_date = prev_day.date

    # Recompute from start_idx forward
    for i in range(start_idx, len(all_days)):
        day = all_days[i]

        # Decay CTL/ATL across any gap since the previous record
        if prev_date is not None:
            gap_days = (day.date - prev_date).days
            if gap_days > 1:
                # Apply exponential decay for each missing day
                # After N days with zero load: value * (1 - decay)^N
                ctl_decay_factor = (1 - ctl_decay) ** (gap_days - 1)
                atl_decay_factor = (1 - atl_decay) ** (gap_days - 1)
                prev_ctl *= ctl_decay_factor
                prev_atl *= atl_decay_factor

        # CTL = CTL_yesterday + (load - CTL_yesterday) * ctl_decay
        day.ctl = prev_ctl + (day.training_load - prev_ctl) * ctl_decay

        # ATL = ATL_yesterday + (load - ATL_yesterday) * atl_decay
        day.atl = prev_atl + (day.training_load - prev_atl) * atl_decay

        # TSB = CTL - ATL
        day.tsb = day.ctl - day.atl

        prev_ctl = day.ctl
        prev_atl = day.atl
        prev_date = day.date

    await db.flush()


def compute_acwr(daily_loads: list[float]) -> float | None:
    """Compute Acute:Chronic Workload Ratio (ACWR).
    
    Acute load = sum of last 7 days
    Chronic load = average of last 28 days (weekly average)
    ACWR = acute / chronic
    
    Returns None if insufficient data (< 7 days).
    """
    if len(daily_loads) < 7:
        return None
    
    # Acute: sum of last 7 days
    acute = sum(daily_loads[-7:])
    
    # Chronic: average of last 28 days (or available data)
    chronic_days = min(28, len(daily_loads))
    chronic_sum = sum(daily_loads[-chronic_days:])
    chronic_avg = chronic_sum / (chronic_days / 7)  # Normalize to weekly
    
    if chronic_avg <= 0:
        return None
    
    return round(acute / chronic_avg, 2)


def acwr_status(acwr: float) -> dict:
    """Return ACWR status and guidance based on Gabbett (2016) thresholds."""
    if acwr < 0.8:
        return {
            "status": "undertrained",
            "color": "#3b82f6",  # blue
            "guidance": "Training load is too low. Risk of de-training.",
        }
    elif acwr <= 1.0:
        return {
            "status": "well-managed",
            "color": "#22c55e",  # green
            "guidance": "Optimal zone. Training is building appropriately.",
        }
    elif acwr <= 1.3:
        return {
            "status": "sweet-spot",
            "color": "#22c55e",  # green
            "guidance": "Productive overload. Stimulating adaptation with manageable risk.",
        }
    elif acwr <= 1.5:
        return {
            "status": "caution",
            "color": "#f59e0b",  # yellow/amber
            "guidance": "Training load rising faster than fitness. Consider pulling back.",
        }
    else:
        return {
            "status": "danger",
            "color": "#ef4444",  # red
            "guidance": "High injury risk. Reduce training load immediately.",
        }
