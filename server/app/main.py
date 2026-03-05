# app.py
import os, sqlite3, time
from fastapi import Depends, FastAPI, Query, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from datetime import datetime, timezone
import threading
from pathlib import Path

app = FastAPI()


from fastapi.middleware.cors import CORSMiddleware

# Allow CORS from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.api.rag_router import router as rag_router

# add endpoints from rag_router.py to the main app, prefixed with /rag, and tagged as 'rag' in the FastAPI /docs UI
app.include_router(rag_router, prefix="/rag", tags=["rag"])

# Load repo-root .env explicitly so behavior is stable across working directories.
DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=DOTENV_PATH)

import uvicorn
from app.api.weather_hourly import get_nws_hourly_weather
from app.api.weather_open_meteo import get_open_meteo_hourly_weather
from app.db.supabase_queries import (
    get_supabase,
    get_supabase_aggregated,
    get_supabase_summary,
    insert_supabase,
    supabase as supabase_client,
)

RAW_DATA_TABLE = os.getenv("RAW_DATA_TABLE", "readings")
SNAPSHOT_DATA_TABLE = os.getenv("SNAPSHOT_DATA_TABLE", "snapshots")

INGEST_TOKEN = os.getenv("INGEST_TOKEN", "")
STATUS_TOKEN = os.getenv("STATUS_TOKEN", "")
NWS_DEFAULT_STATION = os.getenv("NWS_DEFAULT_STATION", "KBFI")
NWS_DEFAULT_TZ = os.getenv("NWS_DEFAULT_TZ", "America/Los_Angeles")
OPEN_METEO_DEFAULT_LAT = float(os.getenv("OPEN_METEO_DEFAULT_LAT", "47.6225"))
OPEN_METEO_DEFAULT_LON = float(os.getenv("OPEN_METEO_DEFAULT_LON", "-122.3118"))

### Index loop ###
@app.on_event("startup")
def start_index_loop():
    from app.scripts.index_loop import index_loop
    thread = threading.Thread(target=index_loop, daemon=True)
    thread.start()

latest_reading = None

@app.get("/ping")
def ping():
    return {"pong": True, "sqlite": True, "supabase": bool(supabase_client)}

@app.get("/latest")
def get_latest(token: str = Query(default="")):
    if token != STATUS_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return latest_reading or {}

@app.post("/ingest")
async def ingest(request: Request, x_token: str = Header(None)):
    global latest_reading
    if x_token != INGEST_TOKEN:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)

    data = await request.json()
    data["ts"] = datetime.now(timezone.utc).isoformat()
    
    # Basic shape guard (keep it loose for now)
    required = {"device_id", "ts"}
    if not required.issubset(set(data.keys())):
        return JSONResponse({"ok": False, "error": "missing device_id or ts"}, status_code=400)

    # Log to console
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), data)

    # Supabase write (if configured)
    sb_status = None
    if supabase_client:
        sb_res = insert_supabase(data)
        sb_status = "ok" if sb_res and getattr(sb_res, "data", None) else "error"

    latest_reading = data

    return {"ok": True, "supabase": sb_status}


@app.get("/timeseries")
def get_readings(
    token: str = Query(default=""), 
    limit: int = Query(default=100, lte=1000),
    offset: int = Query(default=0, ge=0),
    table: str = Query(default=RAW_DATA_TABLE),
    start_ts: str = Query(default=None),
    end_ts: str = Query(default=None),
    device_id: str = Query(default=None),
    order_desc: bool = Query(default=True),
    bucket: int = Query(default=None, ge=1),
    aggregate_mode: str = Query(default="full"),
    ):
    if token != STATUS_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if bucket is not None:
        if table != RAW_DATA_TABLE:
            raise HTTPException(
                status_code=400,
                detail=f"Aggregation currently supports only table='{RAW_DATA_TABLE}'",
            )
        aggregates = get_supabase_aggregated(
            table=table,
            bucket_seconds=bucket,
            start_ts=start_ts,
            end_ts=end_ts,
            device_id=device_id,
            limit=limit,
            offset=offset,
            order_desc=order_desc,
            aggregate_mode="lite" if aggregate_mode == "lite" else "full",
        )
        return {"ok": True, "bucket": bucket, "aggregate_mode": aggregate_mode, "aggregates": aggregates}

    rows = get_supabase(
        table=table, 
        limit=limit, 
        offset=offset, 
        start_ts=start_ts, 
        end_ts=end_ts, 
        device_id=device_id,
        order_desc=order_desc,
        )

    return {"ok": True, table: rows}


@app.get("/timeseries/summary")
def get_readings_summary(
    token: str = Query(default=""),
    table: str = Query(default=RAW_DATA_TABLE),
    start_ts: str = Query(default=None),
    end_ts: str = Query(default=None),
    device_id: str = Query(default=None),
):
    if token != STATUS_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if table != RAW_DATA_TABLE:
        raise HTTPException(
            status_code=400,
            detail=f"Summary currently supports only table='{RAW_DATA_TABLE}'",
        )

    summary = get_supabase_summary(
        table=table,
        start_ts=start_ts,
        end_ts=end_ts,
        device_id=device_id,
    )
    return {"ok": True, "summary": summary}


@app.get("/weather/hourly")
def get_weather_hourly(
    token: str = Query(default=""),
    provider: str = Query(default="noaa"),
    station: str = Query(default=NWS_DEFAULT_STATION),
    latitude: float = Query(default=OPEN_METEO_DEFAULT_LAT),
    longitude: float = Query(default=OPEN_METEO_DEFAULT_LON),
    start_ts: str = Query(default=None),
    end_ts: str = Query(default=None),
    tz: str = Query(default=NWS_DEFAULT_TZ),
    page_limit: int = Query(default=500, ge=1, le=500),
    # 30-day weather pulls may require >50 pages depending on station report cadence.
    max_pages: int = Query(default=10, ge=1, le=200),
):
    if token != STATUS_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        provider_name = provider.lower()
        if provider_name == "openmeteo":
            result = get_open_meteo_hourly_weather(
                latitude=latitude,
                longitude=longitude,
                start_ts=start_ts,
                end_ts=end_ts,
                tz_name=tz,
            )
        else:
            result = get_nws_hourly_weather(
                station=station,
                start_ts=start_ts,
                end_ts=end_ts,
                tz_name=tz,
                page_limit=page_limit,
                max_pages=max_pages,
            )
            result["provider"] = "noaa"
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Weather API fetch failed: {exc!r}") from exc

    return {"ok": True, **result}



if __name__ == "__main__":
    import uvicorn
    # LAN-exposed so ESP32 can reach it
    uvicorn.run(app, host="0.0.0.0", port=8000)
