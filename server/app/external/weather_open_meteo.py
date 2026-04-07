from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json


OPEN_METEO_ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
DEFAULT_USER_AGENT = "esp32_api weather helper (local-dev)"


def _parse_iso_ts(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso_utc(dt: datetime) -> str:
    return (
        dt.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_open_meteo_hourly_weather(
    *,
    latitude: float,
    longitude: float,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    tz_name: str = "America/Los_Angeles",
) -> dict[str, Any]:
    end_dt = _parse_iso_ts(end_ts) or datetime.now(timezone.utc)
    start_dt = _parse_iso_ts(start_ts) or (end_dt - timedelta(days=2))
    if start_dt >= end_dt:
        raise ValueError("start_ts must be before end_ts")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_dt.date().isoformat(),
        "end_date": end_dt.date().isoformat(),
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "dew_point_2m",
                "wind_speed_10m",
            ]
        ),
        "timezone": tz_name,
    }
    url = f"{OPEN_METEO_ARCHIVE_API}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urlopen(req, timeout=30) as resp:
        payload = json.load(resp)

    hourly = payload.get("hourly", {}) or {}
    times = hourly.get("time", []) or []
    temp_vals = hourly.get("temperature_2m", []) or []
    rh_vals = hourly.get("relative_humidity_2m", []) or []
    dp_vals = hourly.get("dew_point_2m", []) or []
    wind_vals = hourly.get("wind_speed_10m", []) or []

    rows: list[dict[str, Any]] = []
    for i, t in enumerate(times):
        try:
            bucket_start = datetime.fromisoformat(t)
        except ValueError:
            continue
        bucket_end = bucket_start + timedelta(hours=1)

        temp = _to_float(temp_vals[i]) if i < len(temp_vals) else None
        rh = _to_float(rh_vals[i]) if i < len(rh_vals) else None
        dp = _to_float(dp_vals[i]) if i < len(dp_vals) else None
        wind = _to_float(wind_vals[i]) if i < len(wind_vals) else None

        rows.append(
            {
                "bucket_start": bucket_start.isoformat(),
                "bucket_end": bucket_end.isoformat(),
                "count": 1,
                "temp_c_avg": temp,
                "temp_c_min": temp,
                "temp_c_max": temp,
                "rh_avg": rh,
                "rh_min": rh,
                "rh_max": rh,
                "dewpoint_c_avg": dp,
                "dewpoint_c_min": dp,
                "dewpoint_c_max": dp,
                "wind_m_s_avg": wind,
                "wind_m_s_min": wind,
                "wind_m_s_max": wind,
            }
        )

    return {
        "provider": "openmeteo",
        "station": None,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": payload.get("timezone") or tz_name,
        "start_ts": _iso_utc(start_dt),
        "end_ts": _iso_utc(end_dt),
        "rows": rows,
    }
