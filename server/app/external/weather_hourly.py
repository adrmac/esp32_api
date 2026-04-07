from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
import json
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


NWS_API_BASE = "https://api.weather.gov"
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


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    return num


def _build_url_with_limit(url: str, limit: int) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["limit"] = str(limit)
    return urlunparse(parsed._replace(query=urlencode(query)))


def fetch_nws_observations(
    *,
    station: str,
    start_ts: datetime,
    end_ts: datetime,
    page_limit: int = 500,
    max_pages: int = 10,
) -> list[dict[str, Any]]:
    url = (
        f"{NWS_API_BASE}/stations/{station}/observations?"
        f"start={_iso_utc(start_ts)}&end={_iso_utc(end_ts)}"
    )
    url = _build_url_with_limit(url, page_limit)
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    features: list[dict[str, Any]] = []
    pages = 0
    while url and pages < max_pages:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as resp:
            payload = json.load(resp)

        page_features = payload.get("features", []) or []
        features.extend(page_features)

        next_url = None
        pagination = payload.get("pagination")
        if isinstance(pagination, dict):
            next_url = pagination.get("next")
        url = (
            _build_url_with_limit(next_url, page_limit)
            if isinstance(next_url, str)
            else None
        )
        pages += 1

    return features


def get_nws_hourly_weather(
    *,
    station: str = "KBFI",
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    tz_name: str = "America/Los_Angeles",
    page_limit: int = 500,
    max_pages: int = 10,
) -> dict[str, Any]:
    try:
        tz = ZoneInfo(tz_name)
        resolved_tz_name = tz_name
    except ZoneInfoNotFoundError:
        tz = timezone.utc
        resolved_tz_name = "UTC"

    end_dt = _parse_iso_ts(end_ts) or datetime.now(timezone.utc)
    start_dt = _parse_iso_ts(start_ts) or (end_dt - timedelta(days=2))
    if start_dt >= end_dt:
        raise ValueError("start_ts must be before end_ts")

    features = fetch_nws_observations(
        station=station,
        start_ts=start_dt,
        end_ts=end_dt,
        page_limit=page_limit,
        max_pages=max_pages,
    )

    buckets: dict[str, dict[str, Any]] = {}

    for feature in features:
        props = feature.get("properties", {}) or {}
        ts_text = props.get("timestamp")
        if not isinstance(ts_text, str):
            continue
        ts = _parse_iso_ts(ts_text)
        if ts is None:
            continue

        local = ts.astimezone(tz)
        hour_bucket = local.replace(minute=0, second=0, microsecond=0)
        key = hour_bucket.isoformat()

        temperature_c = _safe_float((props.get("temperature") or {}).get("value"))
        rh_pct = _safe_float((props.get("relativeHumidity") or {}).get("value"))
        dewpoint_c = _safe_float((props.get("dewpoint") or {}).get("value"))
        wind_m_s = _safe_float((props.get("windSpeed") or {}).get("value"))

        bucket = buckets.get(key)
        if bucket is None:
            bucket = {
                "bucket_start": hour_bucket.isoformat(),
                "bucket_end": (hour_bucket + timedelta(hours=1)).isoformat(),
                "count": 0,
                "temp_c_values": [],
                "rh_values": [],
                "dewpoint_c_values": [],
                "wind_m_s_values": [],
            }
            buckets[key] = bucket

        bucket["count"] += 1
        if temperature_c is not None:
            bucket["temp_c_values"].append(temperature_c)
        if rh_pct is not None:
            bucket["rh_values"].append(rh_pct)
        if dewpoint_c is not None:
            bucket["dewpoint_c_values"].append(dewpoint_c)
        if wind_m_s is not None:
            bucket["wind_m_s_values"].append(wind_m_s)

    def summarize(values: list[float]) -> tuple[Optional[float], Optional[float], Optional[float]]:
        if not values:
            return (None, None, None)
        avg = sum(values) / len(values)
        return (avg, min(values), max(values))

    rows: list[dict[str, Any]] = []
    for key in sorted(buckets.keys()):
        bucket = buckets[key]
        t_avg, t_min, t_max = summarize(bucket["temp_c_values"])
        rh_avg, rh_min, rh_max = summarize(bucket["rh_values"])
        dp_avg, dp_min, dp_max = summarize(bucket["dewpoint_c_values"])
        w_avg, w_min, w_max = summarize(bucket["wind_m_s_values"])

        rows.append(
            {
                "bucket_start": bucket["bucket_start"],
                "bucket_end": bucket["bucket_end"],
                "count": bucket["count"],
                "temp_c_avg": t_avg,
                "temp_c_min": t_min,
                "temp_c_max": t_max,
                "rh_avg": rh_avg,
                "rh_min": rh_min,
                "rh_max": rh_max,
                "dewpoint_c_avg": dp_avg,
                "dewpoint_c_min": dp_min,
                "dewpoint_c_max": dp_max,
                "wind_m_s_avg": w_avg,
                "wind_m_s_min": w_min,
                "wind_m_s_max": w_max,
            }
        )

    return {
        "station": station,
        "timezone": resolved_tz_name,
        "start_ts": _iso_utc(start_dt),
        "end_ts": _iso_utc(end_dt),
        "rows": rows,
    }
