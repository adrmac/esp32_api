from __future__ import annotations

import os
from typing import Any, Literal, Optional

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from supabase import create_client


SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
SUPABASE_DB_URL_IPV4 = os.getenv("SUPABASE_DB_URL_IPV4", "")
RAW_DATA_TABLE = os.getenv("RAW_DATA_TABLE", "readings")
SNAPSHOT_DATA_TABLE = os.getenv("SNAPSHOT_DATA_TABLE", "snapshots")


supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[supabase] client initialized")
    except Exception as exc:
        print("[supabase] init failed:", repr(exc))
        supabase = None
else:
    print("[supabase] missing DATABASE_URL or SUPABASE_*KEY; skipping client")


def insert_supabase(row: dict[str, Any]):
    if supabase is None:
        return None
    try:
        res = supabase.table(RAW_DATA_TABLE).insert([row]).execute()
        print("[supabase] insert data:", getattr(res, "data", None))
        return res
    except Exception as exc:
        print("[supabase] insert error:", repr(exc))
        return None


def get_supabase(
    *,
    table: str = RAW_DATA_TABLE,
    device_id: Optional[str] = None,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    limit: int = 10000,
    offset: int = 0,
    order_desc: bool = True,
) -> list[dict[str, Any]]:
    if supabase is None:
        return []
    try:
        time_column = "window_start" if table == SNAPSHOT_DATA_TABLE else "ts"
        query = (
            supabase.table(table)
            .select("*")
            .order(time_column, desc=order_desc)
            .limit(limit)
            .range(offset, offset + limit - 1)
        )
        if device_id is not None:
            query = query.eq("device_id", device_id)
        if start_ts is not None:
            query = query.gte(time_column, start_ts)
        if end_ts is not None:
            query = query.lte(time_column, end_ts)
        response = query.execute()
        rows = getattr(response, "data", []) or []
        print(
            f"[supabase] get_supabase: got {len(rows)} rows from '{table}' "
            f"(time_column={time_column})"
        )
        return rows
    except Exception as exc:
        print("[supabase] get_supabase error:", repr(exc))
        return []


def get_supabase_aggregated(
    *,
    table: str = RAW_DATA_TABLE,
    bucket_seconds: int,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    device_id: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0,
    order_desc: bool = False,
    aggregate_mode: Literal["full", "lite"] = "full",
) -> list[dict[str, Any]]:
    """Return bucketed sensor aggregates from the raw readings table.

    This function currently supports the raw readings table shape (`ts`, `temp_c`,
    `temp_f`, `rh`, `device_id`). It uses psycopg directly because Supabase's query
    builder is awkward for grouped aggregations.
    """
    if not SUPABASE_DB_URL_IPV4:
        print("[supabase] aggregate query skipped: SUPABASE_DB_URL_IPV4 is missing")
        return []

    if bucket_seconds < 1:
        raise ValueError("bucket_seconds must be >= 1")

    order_direction = sql.SQL("DESC") if order_desc else sql.SQL("ASC")
    where_clause, where_params = _build_timeseries_where_clause(
        device_id=device_id,
        start_ts=start_ts,
        end_ts=end_ts,
    )

    if aggregate_mode == "lite":
        # Strict psycopg/Pylance typing requires sql.SQL objects for dynamic table names, can't do simple f-strings here
        query = sql.SQL(
            """
            select
              date_bin(
                (%(bucket_seconds)s * interval '1 second'),
                ts,
                timestamptz '1970-01-01 00:00:00+00'
              ) as bucket_start,
              date_bin(
                (%(bucket_seconds)s * interval '1 second'),
                ts,
                timestamptz '1970-01-01 00:00:00+00'
              ) + (%(bucket_seconds)s * interval '1 second') as bucket_end,
              date_bin(
                (%(bucket_seconds)s * interval '1 second'),
                ts,
                timestamptz '1970-01-01 00:00:00+00'
              ) as first_ts,
              date_bin(
                (%(bucket_seconds)s * interval '1 second'),
                ts,
                timestamptz '1970-01-01 00:00:00+00'
              ) + (%(bucket_seconds)s * interval '1 second') as last_ts,
              count(*)::int as count,
              avg(temp_f) as temp_f_avg,
              avg(rh) as rh_avg
            from {table}
            {where_clause}
            group by bucket_start
            order by bucket_start {order_direction}
            limit %(limit)s offset %(offset)s;
            """
        ).format(
            table=sql.Identifier(table),
            where_clause=where_clause,
            order_direction=order_direction,
        )
    else:
        # Strict psycopg/Pylance typing requires sql.SQL objects for dynamic table names, can't do simple f-strings here
        query = sql.SQL(
            """
            select
              date_bin(
                (%(bucket_seconds)s * interval '1 second'),
                ts,
                timestamptz '1970-01-01 00:00:00+00'
              ) as bucket_start,
              date_bin(
                (%(bucket_seconds)s * interval '1 second'),
                ts,
                timestamptz '1970-01-01 00:00:00+00'
              ) + (%(bucket_seconds)s * interval '1 second') as bucket_end,
              min(ts) as first_ts,
              max(ts) as last_ts,
              count(*)::int as count,
              avg(temp_c) as temp_c_avg,
              min(temp_c) as temp_c_min,
              max(temp_c) as temp_c_max,
              avg(temp_f) as temp_f_avg,
              min(temp_f) as temp_f_min,
              max(temp_f) as temp_f_max,
              avg(rh) as rh_avg,
              min(rh) as rh_min,
              max(rh) as rh_max
            from {table}
            {where_clause}
            group by bucket_start
            order by bucket_start {order_direction}
            limit %(limit)s offset %(offset)s;
            """
        ).format(
            table=sql.Identifier(table),
            where_clause=where_clause,
            order_direction=order_direction,
        )

    params = {
        "bucket_seconds": bucket_seconds,
        "limit": limit,
        "offset": offset,
    }
    params.update(where_params)

    try:
        with psycopg.connect(SUPABASE_DB_URL_IPV4) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                print(
                    f"[supabase] get_supabase_aggregated: got {len(rows)} rows from '{table}' "
                    f"(bucket_seconds={bucket_seconds})"
                )
                return [dict(row) for row in rows]
    except Exception as exc:
        print("[supabase] get_supabase_aggregated error:", repr(exc))
        return []


def _build_timeseries_where_clause(
    *,
    device_id: Optional[str],
    start_ts: Optional[str],
    end_ts: Optional[str],
) -> tuple[sql.Composable, dict[str, Any]]:
    clauses: list[sql.Composable] = []
    params: dict[str, Any] = {}

    if device_id is not None:
        clauses.append(sql.SQL("device_id = %(device_id)s::text"))
        params["device_id"] = device_id
    if start_ts is not None:
        clauses.append(sql.SQL("ts >= %(start_ts)s::timestamptz"))
        params["start_ts"] = start_ts
    if end_ts is not None:
        clauses.append(sql.SQL("ts <= %(end_ts)s::timestamptz"))
        params["end_ts"] = end_ts

    if not clauses:
        return sql.SQL(""), params

    return sql.SQL("where ") + sql.SQL(" and ").join(clauses), params


def get_supabase_summary(
    *,
    table: str = RAW_DATA_TABLE,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    device_id: Optional[str] = None,
) -> dict[str, Any]:
    """Return lightweight summary metrics for dashboard cards."""
    if not SUPABASE_DB_URL_IPV4:
        print("[supabase] summary query skipped: SUPABASE_DB_URL_IPV4 is missing")
        return {}

    where_clause, where_params = _build_timeseries_where_clause(
        device_id=device_id,
        start_ts=start_ts,
        end_ts=end_ts,
    )

    # Strict psycopg/Pylance typing requires sql.SQL objects for dynamic table names, can't do simple f-strings here
    query = sql.SQL(
        """
        select
          min(ts) as first_ts,
          max(ts) as last_ts,
          count(*)::int as count,
          avg(temp_c) as temp_c_avg,
          avg(temp_f) as temp_f_avg,
          min(temp_f) as temp_f_min,
          max(temp_f) as temp_f_max,
          avg(rh) as rh_avg,
          min(rh) as rh_min,
          max(rh) as rh_max
        from {table}
        {where_clause};
        """
    ).format(
        table=sql.Identifier(table),
        where_clause=where_clause,
    )

    try:
        with psycopg.connect(SUPABASE_DB_URL_IPV4) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, where_params)
                row = cur.fetchone()
                summary = dict(row) if row is not None else {}
                print(
                    f"[supabase] get_supabase_summary: got summary from '{table}' "
                    f"(count={summary.get('count', 0)})"
                )
                return summary
    except Exception as exc:
        print("[supabase] get_supabase_summary error:", repr(exc))
        return {}
