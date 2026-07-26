import datetime
import hashlib
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trace_app.auth import get_current_user
from trace_app.config import settings
from trace_app.database import get_db
from trace_app.models import FitnessTest, User
from trace_app.schemas.fitness_test import FitnessTestChartData, FitnessTestCreate, FitnessTestResponse
from trace_app.services.fit_parser import parse_fit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tests", tags=["fitness-tests"])

TEST_TYPE_UNITS = {
    "ftp": "watts",
    "lthr": "bpm",
    "threshold_pace": "min/km",
    "max_hr": "bpm",
}


@router.post("", response_model=FitnessTestResponse)
async def create_test(
    file: UploadFile,
    test_type: str = Form(...),
    value: float = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    notes: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if test_type not in TEST_TYPE_UNITS:
        raise HTTPException(status_code=400, detail=f"Invalid test type: {test_type}")

    if not file.filename or not file.filename.lower().endswith(".fit"):
        raise HTTPException(status_code=400, detail="Only FIT files are supported for tests")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 50MB limit")

    fit_result = parse_fit(content)
    if not fit_result.points:
        raise HTTPException(status_code=400, detail="No track points found in FIT file")

    storage_dir = Path(settings.storage_dir) / "tests"
    storage_dir.mkdir(parents=True, exist_ok=True)

    file_hash = hashlib.sha256(content).hexdigest()
    ext = "fit"
    file_path = storage_dir / f"{user.id}_{file_hash}.{ext}"
    file_path.write_bytes(content)

    st = datetime.datetime.fromisoformat(start_time)
    et = datetime.datetime.fromisoformat(end_time)

    test = FitnessTest(
        user_id=user.id,
        test_type=test_type,
        value=value,
        unit=TEST_TYPE_UNITS[test_type],
        start_time=st,
        end_time=et,
        fit_file_path=str(file_path),
        notes=notes,
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test


@router.get("", response_model=list[FitnessTestResponse])
async def list_tests(
    test_type: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(FitnessTest).where(FitnessTest.user_id == user.id)
    if test_type:
        q = q.where(FitnessTest.test_type == test_type)
    q = q.order_by(FitnessTest.created_at.desc())
    result = await db.execute(q)
    return result.scalars().all()


@router.delete("/{test_id}")
async def delete_test(
    test_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(FitnessTest).where(FitnessTest.id == test_id, FitnessTest.user_id == user.id)
    test = (await db.execute(q)).scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if test.fit_file_path:
        path = Path(test.fit_file_path)
        if path.exists():
            path.unlink()

    await db.delete(test)
    await db.commit()
    return {"ok": True}


@router.get("/{test_id}/chart", response_model=FitnessTestChartData)
async def get_test_chart(
    test_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(FitnessTest).where(FitnessTest.id == test_id, FitnessTest.user_id == user.id)
    test = (await db.execute(q)).scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if not test.fit_file_path:
        raise HTTPException(status_code=404, detail="FIT file not found")

    path = Path(test.fit_file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="FIT file not found on disk")

    content = path.read_bytes()
    fit_result = parse_fit(content)

    if not fit_result.points:
        raise HTTPException(status_code=400, detail="No track points in FIT file")

    ref_time = fit_result.points[0].time or test.start_time
    timestamps = []
    power = []
    hr = []
    elevation = []
    speed = []

    for p in fit_result.points:
        t = p.time
        if t is None:
            continue
        ts = (t - ref_time).total_seconds()
        timestamps.append(ts)
        power.append(float(p.power) if p.power is not None else None)
        hr.append(float(p.hr) if p.hr is not None else None)
        elevation.append(p.ele)
        speed.append(p.speed)

    return FitnessTestChartData(
        timestamps=timestamps,
        power=power,
        hr=hr,
        elevation=elevation,
        speed=speed,
        fit_start_time=ref_time.isoformat() if ref_time else None,
    )


@router.post("/parse-fit")
async def parse_fit_preview(
    file: UploadFile,
    user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".fit"):
        raise HTTPException(status_code=400, detail="Only FIT files are supported")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 50MB limit")

    fit_result = parse_fit(content)
    if not fit_result.points:
        raise HTTPException(status_code=400, detail="No track points found in FIT file")

    ref_time = fit_result.points[0].time
    timestamps = []
    power = []
    hr = []
    elevation = []
    speed = []

    for p in fit_result.points:
        t = p.time
        if t is None:
            continue
        ts = (t - ref_time).total_seconds() if ref_time else 0
        timestamps.append(ts)
        power.append(float(p.power) if p.power is not None else None)
        hr.append(float(p.hr) if p.hr is not None else None)
        elevation.append(p.ele)
        speed.append(p.speed)

    return FitnessTestChartData(
        timestamps=timestamps,
        power=power,
        hr=hr,
        elevation=elevation,
        speed=speed,
        fit_start_time=ref_time.isoformat() if ref_time else None,
    )
