from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.planning import planner as query_planner


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    def __init__(self, content):
        self.content = content

    def invoke(self, messages):
        return _FakeResponse(self.content)


def test_plan_query_parses_valid_json(monkeypatch) -> None:
    content = """
    {"intent":"aggregate","metric":"temperature_avg","time":{"mode":"relative","relative":{"unit":"hours","value":6}}}
    """
    planner_backend = lambda question: content

    plan = query_planner.plan_query(
        "average temperature over last 6 hours",
        planner_backend=planner_backend,
    )

    assert plan["intent"] == "aggregate"
    assert plan["metric"] == "temperature_avg"
    assert plan["time"]["relative"]["value"] == 6


def test_plan_query_falls_back_when_json_is_invalid(monkeypatch) -> None:
    planner_backend = lambda question: "not json"

    plan = query_planner.plan_query(
        "tell me something",
        planner_backend=planner_backend,
    )

    assert plan["intent"] == "summarize"
    assert plan["metric"] == "none"
    assert plan["time"]["relative"]["unit"] == "hours"
    assert plan["time"]["relative"]["value"] == 24
    assert plan["raw"] == "not json"
    assert "parse_error" in plan


def test_resolve_time_range_for_absolute_window() -> None:
    plan = {
        "time": {
            "mode": "absolute",
            "absolute": {
                "start": "2026-04-07T09:00:00",
                "end": "2026-04-07T11:00:00",
            },
        }
    }

    start_utc, end_utc = query_planner.resolve_time_range(plan)

    assert start_utc.isoformat() == "2026-04-07T16:00:00+00:00"
    assert end_utc.isoformat() == "2026-04-07T18:00:00+00:00"


def test_resolve_time_range_for_day_part(monkeypatch) -> None:
    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 4, 7, 12, 0, 0, tzinfo=tz or ZoneInfo("UTC"))

    monkeypatch.setattr(query_planner, "datetime", _FixedDateTime)

    plan = {
        "time": {
            "mode": "relative",
            "relative": {"day": "yesterday", "part_of_day": "morning"},
        }
    }

    start_utc, end_utc = query_planner.resolve_time_range(plan)

    assert start_utc.isoformat() == "2026-04-06T13:00:00+00:00"
    assert end_utc.isoformat() == "2026-04-06T19:00:00+00:00"
