import asyncio
from datetime import datetime

from fastapi import APIRouter

from app.services.occupancy_forecast import mm1_wait_probability, peak_factor
from app.services.runtime_store import history_as_list

router = APIRouter(prefix="/ml", tags=["occupancy"])


def _occupancy_forecast_payload(
    zone_id: str,
    hour: int | None = None,
    day_of_week: int | None = None,
    wait_minutes: float = 5.0,
) -> dict:
    now = datetime.now()
    h = hour if hour is not None else now.hour
    dow = day_of_week if day_of_week is not None else now.weekday()

    history = history_as_list(zone_id)
    prob = mm1_wait_probability(
        historical_dwell_seconds=history,
        hour=h,
        day_of_week=dow,
        wait_minutes=wait_minutes,
    )
    pf = peak_factor(h, dow)
    return {
        "zone_id": zone_id,
        "hour": h,
        "day_of_week": dow,
        "peak_factor": pf,
        "wait_probability": prob,
        "wait_minutes": wait_minutes,
        "busyness_level": "high" if pf > 0.7 else "medium" if pf > 0.4 else "low",
    }


@router.get("/occupancy-forecast")
async def get_occupancy_forecast(
    zone_id: str,
    hour: int | None = None,
    day_of_week: int | None = None,
    wait_minutes: float = 5.0,
) -> dict:
    return await asyncio.to_thread(
        _occupancy_forecast_payload,
        zone_id,
        hour,
        day_of_week,
        wait_minutes,
    )
