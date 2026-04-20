from __future__ import annotations

from typing import Any, TypedDict


class RelativeTimeSpec(TypedDict, total=False):
    unit: str
    value: int
    day: str
    part_of_day: str


class AbsoluteTimeSpec(TypedDict, total=False):
    start: str
    end: str


class TimeSpec(TypedDict, total=False):
    mode: str
    relative: RelativeTimeSpec
    absolute: AbsoluteTimeSpec


class QueryPlan(TypedDict, total=False):
    intent: str
    metric: str
    time: TimeSpec
    timezone: str
    raw: str
    parse_error: str
