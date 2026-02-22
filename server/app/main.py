# app.py
import os, sqlite3, time
from fastapi import Depends, FastAPI, Query, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from datetime import datetime, timezone
import threading

app = FastAPI()

from app.api.rag_router import router as rag_router

# add endpoints from rag_router.py to the main app, prefixed with /rag, and tagged as 'rag' in the FastAPI /docs UI
app.include_router(rag_router, prefix="/rag", tags=["rag"])

load_dotenv()  # take environment variables from .env file

from supabase import create_client  # pip install supabase
import uvicorn

DATABASE_URL = os.getenv("SUPABASE_URL", "")
# Accept either service role or anon; prefer service role on the server.
DATABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
RAW_DATA_TABLE = os.getenv("RAW_DATA_TABLE", "readings")
SNAPSHOT_DATA_TABLE = os.getenv("SNAPSHOT_DATA_TABLE", "snapshots")

INGEST_TOKEN = os.getenv("INGEST_TOKEN", "")
STATUS_TOKEN = os.getenv("STATUS_TOKEN", "")

supabase = None

if DATABASE_URL and DATABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(DATABASE_URL, DATABASE_KEY)
        print("[supabase] client initialized")
    except Exception as e:
        print("[supabase] init failed:", repr(e))
        supabase = None
else:
    print("[supabase] missing DATABASE_URL or SUPABASE_*KEY; skipping client")


### Index loop ###
@app.on_event("startup")
def start_index_loop():
    from app.scripts.index_loop import index_loop
    thread = threading.Thread(target=index_loop, daemon=True)
    thread.start()



def insert_supabase(row: dict):
    if supabase is None:
        return None
    try:
        # send as a list for maximum compatibility
        res = supabase.table(RAW_DATA_TABLE).insert([row]).execute()
        # Supabase-py v2 returns a Postgres response with .data
        print("[supabase] insert data:", getattr(res, "data", None))
        return res
    except Exception as e:
        print("[supabase] insert error:", repr(e))
        return None


def get_supabase(
        table,
        device_id=None,
        start_ts=None,
        end_ts=None,
        limit=100,
        offset=0,
        order_desc=True,
        time_column=None,
        ):
    if supabase is None:
        return []
    try:
        selected_time_column = time_column
        if selected_time_column is None:
            selected_time_column = "window_start" if table == SNAPSHOT_DATA_TABLE else "ts"

        query = (
            supabase.table(table)
            .select("*")
            .order(selected_time_column, desc=order_desc)
            .limit(limit)
            .range(offset, offset + limit - 1)
        )
        if device_id is not None:
            query = query.eq("device_id", device_id)
        if start_ts is not None:
            query = query.gte(selected_time_column, start_ts)
        if end_ts is not None:
            query = query.lte(selected_time_column, end_ts)
        response = query.execute()
        print(
            f"[supabase] get_supabase: got {len(getattr(response, 'data', []))} rows from '{table}' "
            f"(time_column={selected_time_column})"
        )
        return getattr(response, "data", [])
    except Exception as e:
        print("[supabase] get_supabase error:", repr(e))
        return []



latest_reading = None

@app.get("/ping")
def ping():
    return {"pong": True, "sqlite": True, "supabase": bool(supabase)}

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
    if supabase:
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
    ):
    if token != STATUS_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    rows = get_supabase(
        table=table, 
        limit=limit, 
        offset=offset, 
        start_ts=start_ts, 
        end_ts=end_ts, 
        device_id=device_id
        )

    return {"ok": True, table: rows}



if __name__ == "__main__":
    import uvicorn
    # LAN-exposed so ESP32 can reach it
    uvicorn.run(app, host="0.0.0.0", port=8000)
