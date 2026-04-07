from __future__ import annotations

from app.retrieval.structured import weather


def test_fetch_hourly_weather_routes_to_openmeteo(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_openmeteo(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"provider": "openmeteo", "rows": [{"count": 1}]}

    monkeypatch.setattr(weather, "get_open_meteo_hourly_weather", fake_openmeteo)

    result = weather.fetch_hourly_weather(
        provider="openmeteo",
        latitude=47.5,
        longitude=-122.3,
        start_ts="2026-04-07T00:00:00Z",
        end_ts="2026-04-07T03:00:00Z",
        tz="UTC",
    )

    assert result == {"provider": "openmeteo", "rows": [{"count": 1}]}
    assert captured == {
        "latitude": 47.5,
        "longitude": -122.3,
        "start_ts": "2026-04-07T00:00:00Z",
        "end_ts": "2026-04-07T03:00:00Z",
        "tz_name": "UTC",
    }


def test_fetch_hourly_weather_defaults_to_noaa(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_noaa(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"station": "KBFI", "rows": [{"count": 2}]}

    monkeypatch.setattr(weather, "get_nws_hourly_weather", fake_noaa)

    result = weather.fetch_hourly_weather(
        provider="noaa",
        station="KPAE",
        start_ts="2026-04-07T00:00:00Z",
        end_ts="2026-04-07T06:00:00Z",
        tz="America/Los_Angeles",
        page_limit=25,
        max_pages=3,
    )

    assert result == {
        "provider": "noaa",
        "station": "KBFI",
        "rows": [{"count": 2}],
    }
    assert captured == {
        "station": "KPAE",
        "start_ts": "2026-04-07T00:00:00Z",
        "end_ts": "2026-04-07T06:00:00Z",
        "tz_name": "America/Los_Angeles",
        "page_limit": 25,
        "max_pages": 3,
    }
