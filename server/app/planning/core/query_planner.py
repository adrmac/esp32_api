from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import dateparser

from app.frameworks.langchain.runtime import get_llm

TZ = ZoneInfo("America/Los_Angeles")

PARTS = {
    "morning": (6, 12),
    "afternoon": (12, 18),
    "evening": (18, 22),
    "night": (22, 6),
}

PLANNER_SYSTEM = """
You are a query planner for an IoT sensor dataset.
Given a user question, output ONLY valid JSON (no markdown) describing:
- intent: one of ["aggregate","retrieve","summarize"]
- metric: one of ["temperature_avg","temperature_min","temperature_max","humidity_avg","coverage_gaps","latest_snapshot","none"]
- time: an object describing the time range in natural terms.
Rules:
- If question references today/yesterday/last N hours/days, include that.
- If question references parts of day, use: ["morning","afternoon","evening","night"].
- If no time is given, default to last 24 hours.
- timezone should be "America/Los_Angeles".
"""


def plan_query(question: str) -> dict[str, Any]:
    llm = get_llm()
    response = llm.invoke(
        [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": question},
        ]
    )
    content = response.content
    text = content if isinstance(content, str) else json.dumps(content)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        return {
            "intent": "summarize",
            "metric": "none",
            "time": {"mode": "relative", "relative": {"unit": "hours", "value": 24}},
            "timezone": "America/Los_Angeles",
            "parse_error": str(exc),
            "raw": text,
        }


def resolve_time_range(plan: dict[str, Any]) -> tuple[datetime, datetime]:
    now_local = datetime.now(TZ)
    time_obj = plan.get("time", {})
    mode = time_obj.get("mode", "relative")

    if mode == "absolute":
        start = datetime.fromisoformat(time_obj["absolute"]["start"]).replace(
            tzinfo=TZ
        )
        end = datetime.fromisoformat(time_obj["absolute"]["end"]).replace(tzinfo=TZ)
        return start.astimezone(timezone.utc), end.astimezone(timezone.utc)

    relative = time_obj.get("relative", {})

    if "unit" in relative and "value" in relative:
        unit = relative["unit"]
        value = int(relative["value"])
        delta = timedelta(hours=value) if unit == "hours" else timedelta(days=value)
        start_local = now_local - delta
        end_local = now_local
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

    if "day" in relative:
        day = relative["day"]
        part = relative.get("part_of_day")
        base = (
            now_local.date()
            if day == "today"
            else (now_local.date() - timedelta(days=1))
        )
        if part:
            h0, h1 = PARTS[part]
            start_local = datetime(
                base.year, base.month, base.day, h0, 0, 0, tzinfo=TZ
            )
            end_local = datetime(
                base.year, base.month, base.day, h1 % 24, 0, 0, tzinfo=TZ
            )
            if h1 == 24:
                end_local = end_local + timedelta(days=1)
        else:
            start_local = datetime(
                base.year, base.month, base.day, 0, 0, 0, tzinfo=TZ
            )
            end_local = start_local + timedelta(days=1)
        return start_local.astimezone(timezone.utc), end_local.astimezone(
            timezone.utc
        )

    dt = dateparser.parse(
        str(plan.get("raw", "")),
        settings={
            "RELATIVE_BASE": now_local,
            "TIMEZONE": "America/Los_Angeles",
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "past",
        },
    )

    if dt:
        start_local = dt.replace(minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(hours=6)
        return start_local.astimezone(timezone.utc), end_local.astimezone(
            timezone.utc
        )

    start_local = now_local - timedelta(hours=24)
    end_local = now_local
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
