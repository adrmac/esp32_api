from __future__ import annotations

import os

from app.external.weather_hourly import get_nws_hourly_weather
from app.external.weather_open_meteo import get_open_meteo_hourly_weather


NWS_DEFAULT_STATION = os.getenv("NWS_DEFAULT_STATION", "KBFI")
NWS_DEFAULT_TZ = os.getenv("NWS_DEFAULT_TZ", "America/Los_Angeles")
OPEN_METEO_DEFAULT_LAT = float(os.getenv("OPEN_METEO_DEFAULT_LAT", "47.6225"))
OPEN_METEO_DEFAULT_LON = float(os.getenv("OPEN_METEO_DEFAULT_LON", "-122.3118"))


def fetch_hourly_weather(
    *,
    provider: str = "noaa",
    station: str = NWS_DEFAULT_STATION,
    latitude: float = OPEN_METEO_DEFAULT_LAT,
    longitude: float = OPEN_METEO_DEFAULT_LON,
    start_ts: str | None = None,
    end_ts: str | None = None,
    tz: str = NWS_DEFAULT_TZ,
    page_limit: int = 500,
    max_pages: int = 10,
) -> dict[str, object]:
    provider_name = provider.lower()
    if provider_name == "openmeteo":
        return get_open_meteo_hourly_weather(
            latitude=latitude,
            longitude=longitude,
            start_ts=start_ts,
            end_ts=end_ts,
            tz_name=tz,
        )

    result = get_nws_hourly_weather(
        station=station,
        start_ts=start_ts,
        end_ts=end_ts,
        tz_name=tz,
        page_limit=page_limit,
        max_pages=max_pages,
    )
    result["provider"] = "noaa"
    return result
