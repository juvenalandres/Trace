"""Backfill hr_zone_seconds for existing activities.

Run: python -m scripts.backfill_hr_zones
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from trace_app.database import async_session
from trace_app.models.activity import Activity
from trace_app.models.activity_stats import ActivityStats
from trace_app.models.user_zone import UserZone
from trace_app.services.activity_processor import compute_hr_zone_seconds

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill():
    async with async_session() as db:
        q = (
            select(ActivityStats)
            .where(
                ActivityStats.simplified_time_series.isnot(None),
                ActivityStats.hr_zone_seconds.is_(None),
            )
        )
        result = await db.execute(q)
        stats_rows = result.scalars().all()
        logger.info(f"Found {len(stats_rows)} activities to backfill")

        updated = 0
        skipped = 0
        for stats in stats_rows:
            act_q = select(Activity).where(Activity.id == stats.activity_id)
            act_result = await db.execute(act_q)
            activity = act_result.scalar_one_or_none()
            if not activity:
                skipped += 1
                continue

            zone_q = (
                select(UserZone)
                .where(UserZone.user_id == activity.user_id, UserZone.zone_type == "hr")
                .order_by(UserZone.valid_from.desc().nullslast())
                .limit(1)
            )
            zone_result = await db.execute(zone_q)
            user_zone = zone_result.scalar_one_or_none()
            if not user_zone:
                skipped += 1
                continue

            zones = []
            for i in range(1, 6):
                z_min = getattr(user_zone, f"zone_{i}_min", None)
                z_max = getattr(user_zone, f"zone_{i}_max", None)
                if z_min is not None and z_max is not None:
                    zones.append({"min": z_min, "max": z_max})
            if not zones:
                skipped += 1
                continue

            ts_data = json.loads(stats.simplified_time_series)
            stats.hr_zone_seconds = compute_hr_zone_seconds(ts_data, zones)
            updated += 1

            if updated % 50 == 0:
                await db.flush()
                logger.info(f"  ...{updated} updated so far")

        await db.commit()
        logger.info(f"Done: {updated} updated, {skipped} skipped (no zones or no activity)")


if __name__ == "__main__":
    asyncio.run(backfill())
