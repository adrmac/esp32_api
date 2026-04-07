from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import require_status_token
from app.retrieval.structured.weather import fetch_hourly_weather


router = APIRouter()

NWS_DEFAULT_STATION = os.getenv("NWS_DEFAULT_STATION", "KBFI")
NWS_DEFAULT_TZ = os.getenv("NWS_DEFAULT_TZ", "America/Los_Angeles")
OPEN_METEO_DEFAULT_LAT = float(os.getenv("OPEN_METEO_DEFAULT_LAT", "47.6225"))
OPEN_METEO_DEFAULT_LON = float(os.getenv("OPEN_METEO_DEFAULT_LON", "-122.3118"))


@router.get("/weather/hourly", dependencies=[Depends(require_status_token)])
def get_weather_hourly(
    provider: str = Query(default="noaa"),
    station: str = Query(default=NWS_DEFAULT_STATION),
    latitude: float = Query(default=OPEN_METEO_DEFAULT_LAT),
    longitude: float = Query(default=OPEN_METEO_DEFAULT_LON),
    start_ts: str | None = Query(default=None),
    end_ts: str | None = Query(default=None),
    tz: str = Query(default=NWS_DEFAULT_TZ),
    page_limit: int = Query(default=500, ge=1, le=500),
    max_pages: int = Query(default=10, ge=1, le=200),
):
    try:
        result = fetch_hourly_weather(
            provider=provider,
            station=station,
            latitude=latitude,
            longitude=longitude,
            start_ts=start_ts,
            end_ts=end_ts,
            tz=tz,
            page_limit=page_limit,
            max_pages=max_pages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Weather API fetch failed: {exc!r}"
        ) from exc

    return {"ok": True, **result}
