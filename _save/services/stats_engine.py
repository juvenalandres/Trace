import datetime
from calendar import month_name

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from strava_alt.models.activity import Activity
from strava_alt.models.gear import Gear
from strava_alt.schemas.activity import (
    ActivitySummary,
    DashboardResponse,
    EddingtonDistributionPoint,
    EddingtonResponse,
    GearStats,
    MonthlyDay,
    MonthlyResponse,
    PeriodStats,
    PersonalRecords,
    SportBreakdown,
    StatisticsOverview,
    VolumePeriod,
    YearInReview,
    YearMonthSummary,
)
from strava_alt.services.eddington import compute_eddington, eddington_progress

MILES_IN_METERS = 1609.34


class StatsEngine:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def _base_query(self, sport_type: str | None = None, start_date: datetime.date | None = None, end_date: datetime.date | None = None):
        q = select(Activity).where(Activity.user_id == self.user_id)
        if sport_type:
            q = q.where(Activity.sport_type == sport_type)
        if start_date:
            q = q.where(Activity.start_time >= start_date)
        if end_date:
            q = q.where(Activity.start_time < end_date + datetime.timedelta(days=1))
        return q

    async def _agg_query(self, sport_type: str | None = None, start_date: datetime.date | None = None, end_date: datetime.date | None = None):
        q = select(
            func.coalesce(func.sum(Activity.distance_meters), 0),
            func.coalesce(func.sum(Activity.duration_seconds), 0),
            func.coalesce(func.sum(Activity.elevation_gain_meters), 0),
            func.count(Activity.id),
        ).where(Activity.user_id == self.user_id, Activity.distance_meters.isnot(None))
        if sport_type:
            q = q.where(Activity.sport_type == sport_type)
        if start_date:
            q = q.where(Activity.start_time >= start_date)
        if end_date:
            q = q.where(Activity.start_time < end_date + datetime.timedelta(days=1))
        return q

    async def period_stats(self, start_date: datetime.date, end_date: datetime.date | None = None) -> PeriodStats:
        q = await self._agg_query(start_date=start_date, end_date=end_date)
        r = (await self.db.execute(q)).one()
        return PeriodStats(distance_meters=r[0], duration_seconds=r[1], elevation_gain_meters=r[2], activity_count=r[3])

    async def sport_breakdown(self, start_date: datetime.date | None = None, end_date: datetime.date | None = None) -> list[SportBreakdown]:
        q = select(
            Activity.sport_type,
            func.coalesce(func.sum(Activity.distance_meters), 0),
            func.coalesce(func.sum(Activity.duration_seconds), 0),
            func.count(Activity.id),
        ).where(
            Activity.user_id == self.user_id,
            Activity.distance_meters.isnot(None),
        )
        if start_date:
            q = q.where(Activity.start_time >= start_date)
        if end_date:
            q = q.where(Activity.start_time < end_date + datetime.timedelta(days=1))
        q = q.group_by(Activity.sport_type)
        rows = (await self.db.execute(q)).all()
        return [SportBreakdown(sport_type=r[0], distance_meters=r[1], duration_seconds=r[2], activity_count=r[3]) for r in rows]

    async def recent_activities(self, limit: int = 10) -> list[ActivitySummary]:
        q = (select(Activity).where(Activity.user_id == self.user_id)
             .order_by(Activity.start_time.desc()).limit(limit))
        rows = (await self.db.execute(q)).scalars().all()
        return [ActivitySummary.model_validate(r) for r in rows]

    async def dashboard(self) -> DashboardResponse:
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.date()
        week_start = today - datetime.timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        week = await self.period_stats(week_start)
        month = await self.period_stats(month_start)
        year = await self.period_stats(year_start)
        all_time = await self.period_stats(datetime.date(2000, 1, 1))
        by_sport = await self.sport_breakdown()
        recent = await self.recent_activities()

        return DashboardResponse(week=week, month=month, year=year, all_time=all_time, by_sport=by_sport, recent=recent)

    async def monthly(self, year: int, month: int) -> MonthlyResponse:
        start = datetime.date(year, month, 1)
        end = (start + datetime.timedelta(days=32)).replace(day=1)
        days_in_month = (end - start).days

        q = select(Activity).where(
            Activity.user_id == self.user_id,
            Activity.start_time >= start,
            Activity.start_time < end,
        ).order_by(Activity.start_time)
        rows = (await self.db.execute(q)).scalars().all()

        days_map: dict[str, MonthlyDay] = {}
        totals = {"dist": 0.0, "dur": 0.0, "elev": 0.0, "count": 0}
        for a in rows:
            day_key = str(a.start_time.day)
            if day_key not in days_map:
                days_map[day_key] = MonthlyDay()
            d = days_map[day_key]
            d.distance_meters += a.distance_meters or 0
            d.duration_seconds += a.duration_seconds or 0
            d.elevation_gain_meters += a.elevation_gain_meters or 0
            d.activity_count += 1
            d.activities.append(ActivitySummary.model_validate(a))
            totals["dist"] += a.distance_meters or 0
            totals["dur"] += a.duration_seconds or 0
            totals["elev"] += a.elevation_gain_meters or 0
            totals["count"] += 1

        for d in range(1, days_in_month + 1):
            days_map.setdefault(str(d), MonthlyDay())

        return MonthlyResponse(
            year=year, month=month, days=days_map,
            total_distance_meters=totals["dist"], total_duration_seconds=totals["dur"],
            total_elevation_gain_meters=totals["elev"], activity_count=totals["count"],
        )

    async def eddington(self) -> EddingtonResponse:
        result = await self.db.execute(
            select(Activity.distance_meters).where(
                Activity.user_id == self.user_id,
                Activity.distance_meters.isnot(None),
            )
        )
        distances = [row[0] for row in result.all()]

        e = compute_eddington(distances)
        next_e = e + 1
        qualified = eddington_progress(distances, next_e)
        needed = max(0, next_e - qualified)

        result2 = await self.db.execute(
            select(Activity.sport_type, Activity.distance_meters).where(
                Activity.user_id == self.user_id,
                Activity.distance_meters.isnot(None),
            )
        )
        sport_distances: dict[str, list[float]] = {}
        for sport, d in result2.all():
            sport_distances.setdefault(sport, []).append(d)

        sport_breakdown = {}
        for sport, sport_dists in sport_distances.items():
            sport_breakdown[sport] = compute_eddington(sport_dists)

        distances_miles = sorted([d / MILES_IN_METERS for d in distances], reverse=True)
        distribution = []
        seen = set()
        for i, d in enumerate(distances_miles, start=1):
            key = int(d)
            if key not in seen:
                seen.add(key)
                distribution.append({"distance_miles": float(key), "activity_count": i})
        distribution.sort(key=lambda x: x["distance_miles"])

        threshold_meters = next_e * MILES_IN_METERS
        recent_rows = await self.db.execute(
            select(Activity).where(
                Activity.user_id == self.user_id,
                Activity.distance_meters.isnot(None),
                Activity.distance_meters >= threshold_meters,
            ).order_by(Activity.distance_meters).limit(20)
        )
        recent = [ActivitySummary.model_validate(r) for r in recent_rows.scalars().all()]

        return EddingtonResponse(
            eddington_number=e, next_milestone=next_e,
            activities_qualified_for_next=qualified, activities_needed_for_next=needed,
            sport_breakdown=sport_breakdown,
            distribution=[EddingtonDistributionPoint(**d) for d in distribution],
            recent_qualifying=recent,
        )

    async def year_in_review(self, year: int) -> YearInReview:
        start = datetime.date(year, 1, 1)
        end = datetime.date(year + 1, 1, 1)

        totals_q = await self._agg_query(start_date=start, end_date=end)
        totals_r = (await self.db.execute(totals_q)).one()

        by_sport = await self.sport_breakdown(start_date=start, end_date=end)

        monthly = []
        for m in range(1, 13):
            ms = datetime.date(year, m, 1)
            me = datetime.date(year, m + 1, 1) if m < 12 else end
            q = await self._agg_query(start_date=ms, end_date=me)
            r = (await self.db.execute(q)).one()
            monthly.append(YearMonthSummary(month=m, distance_meters=r[0], duration_seconds=r[1], elevation_gain_meters=r[2], activity_count=r[3]))

        pr = await self._personal_records(start_date=start, end_date=end)

        best_month = max(monthly, key=lambda x: x.distance_meters) if monthly else None
        best_sport = max(by_sport, key=lambda x: x.distance_meters) if by_sport else None

        return YearInReview(
            year=year,
            total_distance_meters=totals_r[0], total_duration_seconds=totals_r[1],
            total_elevation_gain_meters=totals_r[2], activity_count=totals_r[3],
            by_sport=by_sport, monthly=monthly, personal_records=pr,
            favorite_month=month_name[best_month.month] if best_month else None,
            favorite_sport=best_sport.sport_type if best_sport else None,
        )

    async def _personal_records(self, sport_type: str | None = None, start_date: datetime.date | None = None, end_date: datetime.date | None = None) -> PersonalRecords:
        async def best(col, asc=False):
            q = select(Activity).where(
                Activity.user_id == self.user_id,
                col.isnot(None),
            )
            if sport_type:
                q = q.where(Activity.sport_type == sport_type)
            if start_date:
                q = q.where(Activity.start_time >= start_date)
            if end_date:
                q = q.where(Activity.start_time < end_date)
            q = q.order_by(col.asc() if asc else col.desc()).limit(1)
            r = (await self.db.execute(q)).scalars().first()
            return ActivitySummary.model_validate(r) if r else None

        return PersonalRecords(
            longest_distance_meters=await best(Activity.distance_meters),
            longest_duration_seconds=await best(Activity.duration_seconds),
            highest_elevation_gain_meters=await best(Activity.elevation_gain_meters),
            fastest_avg_speed=await best(Activity.avg_speed),
            highest_avg_heartrate=await best(Activity.avg_heartrate),
            highest_calories=await best(Activity.calories),
            max_speed=await best(Activity.max_speed),
        )

    async def personal_records(self, sport_type: str | None = None) -> PersonalRecords:
        return await self._personal_records(sport_type=sport_type)

    async def gear_stats(self) -> list[GearStats]:
        result = await self.db.execute(
            select(
                Gear.id, Gear.name, Gear.gear_type, Gear.brand, Gear.model,
                Gear.nickname, Gear.retired, Gear.maintenance_interval_km,
                func.coalesce(func.sum(Activity.distance_meters), 0),
                func.coalesce(func.sum(Activity.duration_seconds), 0),
                func.coalesce(func.sum(Activity.elevation_gain_meters), 0),
                func.count(Activity.id),
                func.max(Activity.start_time),
            ).outerjoin(Activity, Activity.gear_id == Gear.id)
             .where(Gear.user_id == self.user_id)
             .group_by(Gear.id)
             .order_by(Gear.name)
        )
        rows = result.all()
        out = []
        for r in rows:
            interval = r.maintenance_interval_km
            total_km = r[8] / 1000 if r[8] else 0
            out.append(GearStats(
                id=r.id, name=r.name, gear_type=r.gear_type, brand=r.brand,
                model=r.model, nickname=r.nickname, retired=r.retired,
                total_distance_meters=r[8], total_duration_seconds=r[9],
                total_elevation_gain_meters=r[10], activity_count=r[11],
                last_used=str(r[12].date()) if r[12] else None,
                maintenance_interval_km=interval,
                maintenance_overdue=bool(interval and total_km >= interval),
            ))
        return out

    async def volume_over_time(self, period: str, sport_type: str | None = None, year: int | None = None) -> list[VolumePeriod]:
        if period == "week":
            return await self._volume_by_iso_week(sport_type, year)
        elif period == "month":
            return await self._volume_by_month(sport_type, year)
        else:
            return await self._volume_by_year(sport_type)

    async def _volume_by_iso_week(self, sport_type: str | None = None, year: int | None = None) -> list[VolumePeriod]:
        q = select(
            func.strftime("%Y-W%W", Activity.start_time).label("period"),
            func.coalesce(func.sum(Activity.distance_meters), 0),
            func.coalesce(func.sum(Activity.duration_seconds), 0),
            func.coalesce(func.sum(Activity.elevation_gain_meters), 0),
            func.count(Activity.id),
        ).where(Activity.user_id == self.user_id, Activity.distance_meters.isnot(None))
        if sport_type:
            q = q.where(Activity.sport_type == sport_type)
        if year:
            q = q.where(func.extract("year", Activity.start_time) == year)
        q = q.group_by("period").order_by("period")
        rows = (await self.db.execute(q)).all()
        return [VolumePeriod(period_start=r[0], distance_meters=r[1], duration_seconds=r[2], elevation_gain_meters=r[3], activity_count=r[4]) for r in rows]

    async def _volume_by_month(self, sport_type: str | None = None, year: int | None = None) -> list[VolumePeriod]:
        q = select(
            func.strftime("%Y-%m", Activity.start_time).label("period"),
            func.coalesce(func.sum(Activity.distance_meters), 0),
            func.coalesce(func.sum(Activity.duration_seconds), 0),
            func.coalesce(func.sum(Activity.elevation_gain_meters), 0),
            func.count(Activity.id),
        ).where(Activity.user_id == self.user_id, Activity.distance_meters.isnot(None))
        if sport_type:
            q = q.where(Activity.sport_type == sport_type)
        if year:
            q = q.where(func.extract("year", Activity.start_time) == year)
        q = q.group_by("period").order_by("period")
        rows = (await self.db.execute(q)).all()
        return [VolumePeriod(period_start=r[0], distance_meters=r[1], duration_seconds=r[2], elevation_gain_meters=r[3], activity_count=r[4]) for r in rows]

    async def _volume_by_year(self, sport_type: str | None = None) -> list[VolumePeriod]:
        q = select(
            func.strftime("%Y", Activity.start_time).label("period"),
            func.coalesce(func.sum(Activity.distance_meters), 0),
            func.coalesce(func.sum(Activity.duration_seconds), 0),
            func.coalesce(func.sum(Activity.elevation_gain_meters), 0),
            func.count(Activity.id),
        ).where(Activity.user_id == self.user_id, Activity.distance_meters.isnot(None))
        if sport_type:
            q = q.where(Activity.sport_type == sport_type)
        q = q.group_by("period").order_by("period")
        rows = (await self.db.execute(q)).all()
        return [VolumePeriod(period_start=r[0], distance_meters=r[1], duration_seconds=r[2], elevation_gain_meters=r[3], activity_count=r[4]) for r in rows]

    async def overview(self) -> StatisticsOverview:
        q = await self._agg_query()
        r = (await self.db.execute(q)).one()
        count = r[3]
        avg_dist = r[0] / count if count else 0
        avg_dur = r[1] / count if count else 0
        avg_spd = r[0] / r[1] if r[1] else 0
        return StatisticsOverview(
            activity_count=count, total_distance_meters=r[0],
            total_duration_seconds=r[1], total_elevation_gain_meters=r[2],
            avg_distance_meters=avg_dist, avg_duration_seconds=avg_dur,
            avg_speed=avg_spd,
        )

    async def available_years(self) -> list[int]:
        q = select(
            func.extract("year", Activity.start_time).label("y")
        ).where(
            Activity.user_id == self.user_id,
        ).group_by("y").order_by("y")
        rows = (await self.db.execute(q)).all()
        return [int(r[0]) for r in rows]
