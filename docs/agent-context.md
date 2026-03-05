# Agent Context

## Current objective
Fix psycopg/Pylance `execute()` typing errors in RAG modules after venv recreation.

## What changed
- Updated `server/app/rag/rag_query.py`:
  - Added `from psycopg import sql`.
  - Replaced dynamic f-string SQL in `fetch_snapshots_between()` with `sql.SQL(...).format(table=sql.Identifier(table))`.
  - Added comment above query block:
    - `# Strict psycopg/Pylance typing requires sql.SQL objects for dynamic table names, can't do simple f-strings here`
- Updated `server/app/rag/rag_snapshots.py`:
  - Added `from psycopg import sql`.
  - Replaced dynamic SQL in `_get_earliest_timestamp()` with typed `sql.SQL` + `sql.Identifier` for table/column names.
  - Replaced dynamic SQL in `_fetch_hour_stats()` with typed `sql.SQL` + `sql.Identifier` for table/column names.
  - Added same strict-typing comment above both query blocks.
- Verified module imports in active server venv:
  - `app.rag.rag_query` OK
  - `app.rag.rag_snapshots` OK

## Next step
Run Pylance/VS Code diagnostics refresh and confirm the previous `QueryNoTemplate` warnings are gone in all three files.

## Blockers/risks
- If additional Pylance warnings remain, they may be in other files with dynamic SQL or due to editor cache; restart language server if needed.

## Branch and latest commit hash
- Branch: (not checked in this task)
- Latest commit hash: (not checked in this task)

## Milestone update: Pylance cleanup (deps.py, rag_query.py, rag_snapshots.py)
- Ran `pyright` against the three files and fixed all reported type errors.
- `server/app/rag/deps.py`:
  - Replaced `.response` attribute access with `str(...)` in `TemperatureSafetyEngine.custom_query` for broader response compatibility.
  - Switched `RetrieverQueryEngine.from_args(..., response_mode=...)` to `ResponseMode.SIMPLE_SUMMARIZE`.
- `server/app/rag/rag_query.py`:
  - `Source` dataclass fields changed to `Optional[str]` because metadata lookups can be `None`.
  - Hardened planner response text extraction for non-string LLM content.
  - Fixed `dateparser.parse` fallback to parse a string (`plan['raw']`) rather than a dict.
  - Relaxed `print_sources` input typing to handle broader query response variants.
- `server/app/rag/rag_snapshots.py`:
  - Added safe handling for `fetchone()` returning `None`.
  - Guarded missing earliest timestamp path and return empty windows.
  - Fixed row null-check ordering before indexing/count conversion.
- Validation: `pyright app/rag/deps.py app/rag/rag_query.py app/rag/rag_snapshots.py` returns `0 errors`.

## Milestone update: api/query.py typing
- Fixed `app/api/query.py` pyright error by constructing `QueryReq(question=query)` before calling `rag_query(...)`.
- Removed unused intermediate `json` dict in the helper.
- Validation: `pyright app/api/query.py` returns `0 errors`.

## Milestone update: llama-index-readers-web/playwright blocker
- Root cause confirmed: server env is `Linux aarch64` + Python 3.12. `playwright` has no matching distribution in this environment, so `llama-index-readers-web` cannot be installed.
- Updated `server/app/rag/ingest_docs.py` to make web ingestion resilient without `llama-index-readers-web`:
  - Added fallback loader using `requests` + `BeautifulSoup`.
  - Kept preferred path when `llama_index.readers.web.SimpleWebPageReader` is available.
  - Removed static import; now uses `importlib.import_module` to avoid Pylance missing-import error.
  - `pyright app/rag/ingest_docs.py` reports 0 errors.
- Updated `requirements.txt`:
  - Commented out `llama-index-readers-web==0.5.6` with note that it is optional on this platform.

## Follow-up risk discovered
- `pip check` reports broken llama-index-core installation (`Ignoring invalid distribution ~lama-index-core` and packages requiring `llama-index-core` not installed).
- Also reports supabase subpackage version mismatch (`supabase 2.28.0` vs `2.27.0` subpackages).
- Next cleanup step: reinstall/pin llama-index stack and supabase stack consistently.

## Milestone update: dependency cleanup pass
- Re-checked environment health:
  - `pip check` => `No broken requirements found`.
  - Installed versions now align with repo pins for `llama-index` and `supabase` stacks.
- Verification imports succeed:
  - `psycopg`, `psycopg_pool`, `langchain_postgres`
  - `app.rag.deps`, `app.rag.rag_query`, `app.rag.rag_snapshots`, `app.rag.rag_index`, `app.rag.ingest_docs`
  - `app.api.query`, `app.api.rag_router`
- Static typing verification:
  - `pyright app/rag/deps.py app/rag/rag_query.py app/rag/rag_snapshots.py app/rag/ingest_docs.py app/api/query.py` => `0 errors`.
- Remaining operational caveat (not dependency-related):
  - In fallback web ingestion path, some URLs return `403` (e.g., Wikipedia/MDPI) when fetched via plain requests in this environment.

## Milestone update: explicit .env loading in main.py
- Updated `server/app/main.py` to load `.env` via explicit repo-root path:
  - `DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"`
  - `load_dotenv(dotenv_path=DOTENV_PATH)`
- This removes dependency on shell working directory for env loading.
- Validation: importing `app.main` shows `DOTENV_PATH=/workspaces/esp32_api/.env` and `STATUS_TOKEN` is loaded.

## Milestone update: /timeseries snapshots fix
- Root cause: `get_supabase()` always used `ts` for ordering/filtering, but snapshot rows are keyed by `window_start`/`window_end`.
- Updated `server/app/main.py`:
  - Added optional `time_column` argument to `get_supabase()`.
  - Added table-aware default: `window_start` for `SNAPSHOT_DATA_TABLE`, otherwise `ts`.
  - Applied selected time column to `.order(...)`, `.gte(...)`, and `.lte(...)`.
  - Extended debug log with chosen time column.
- Validation: `pyright app/main.py` returns `0 errors`.

## Milestone update: deployment readiness check for Cloud Run
- Verified basic dependency consistency in active server venv: `pip check` => `No broken requirements found`.
- Verified app import/start sanity: `from app.main import app` succeeds.
- Noted runtime mismatch to review before deploy:
  - `runtime.txt` requests `python-3.10.11`.
  - Local active venv is Python `3.12.9`.
- Risk note: dependency resolution can differ between 3.12 (local) and 3.10 (Cloud Run) if any pinned package dropped/changed 3.10 wheels.

## Milestone update: Cloud Build trigger diagnosis
- Confirmed repo currently has no `Dockerfile` and no `cloudbuild.yaml`.
- This explains trigger error: manual Cloud Build trigger requires a build definition in repo or trigger config.
- Likely prior deployment path used Cloud Run source deploy/buildpacks rather than standalone Cloud Build trigger from repo files.
- Next step options: add `cloudbuild.yaml`, add `Dockerfile`, or deploy directly from source in Cloud Run UI/CLI.

## Milestone update: Cloud Run vs Cloud Build flow clarification
- Clarified that "Connect repository" in Cloud Build only creates SCM connection metadata; it does not define build type by itself.
- The old working flow likely used Cloud Run source deploy with buildpacks settings (configured in Cloud Run deploy UI), not a standalone Cloud Build trigger requiring a repo `Dockerfile`/`cloudbuild.yaml`.
- For current repo layout (`requirements.txt` at root, app import path under `server/app`), recommended start command for buildpacks is to set `PYTHONPATH=server` and run `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

## Milestone update: Cloud Run URL continuity guidance
- Clarified that service URL stays the same if deploying new revisions to the existing Cloud Run service name.
- Recommended creating a new trigger (or source deploy) that targets the existing service, rather than creating a new service.

## Milestone update: server-side aggregation helper draft
- Added `server/app/db/supabase_queries.py` with `get_supabase_aggregated()` using `psycopg` + parameterized SQL (`date_bin`) for on-demand bucketed aggregation.
- Added `server/app/db/__init__.py` package file.
- Updated `server/app/main.py`:
  - imports `get_supabase_aggregated`
  - adds optional `/timeseries` query param `bucket` (seconds)
  - returns raw rows when `bucket` omitted
  - returns `{ ok, bucket, aggregates }` when `bucket` provided
  - rejects aggregation for non-`readings` tables for now
  - cleaned duplicate `load_dotenv()` call, keeping explicit repo-root `.env` load
- Validation: `pyright app/main.py app/db/supabase_queries.py` => `0 errors`.
- Caveat: aggregate helper requires `SUPABASE_DB_URL_IPV4` (direct Postgres connection URL); raw `/timeseries` path still works with only `SUPABASE_URL` + key.

## Milestone update: moved Supabase raw helpers into db module
- Moved `insert_supabase()` and raw `get_supabase()` from `server/app/main.py` to `server/app/db/supabase_queries.py`.
- Centralized Supabase REST client initialization in `server/app/db/supabase_queries.py` and exported `supabase` for health checks.
- Updated `server/app/main.py` to import and use:
  - `insert_supabase`
  - `get_supabase`
  - `get_supabase_aggregated`
  - `supabase as supabase_client`
- `ping()` now reports `bool(supabase_client)`.
- Validation:
  - `pyright app/main.py app/db/supabase_queries.py` => `0 errors`
  - import smoke test succeeds and raw helper returns rows.

## Milestone update: aggregate endpoint empty-array root cause fixed
- Diagnosed `useESP32Aggregates` returning empty array with no frontend error.
- Root cause was backend SQL in `get_supabase_aggregated()`:
  - Postgres `AmbiguousParameter` when optional params were `None` in predicates like `(%(device_id)s is null or device_id = %(device_id)s)`.
  - Helper catches exceptions and returned `[]`, so frontend saw no HTTP error.
- Fixed by casting parameter placeholders in SQL:
  - `%(device_id)s::text`
  - `%(start_ts)s::timestamptz`
  - `%(end_ts)s::timestamptz`
- Verified aggregate helper now returns rows for 7-day / 1-hour bucket query.

## Milestone update: aggregate bucket metadata fields added
- Extended `get_supabase_aggregated()` SQL output with:
  - `bucket_end`
  - `first_ts`
  - `last_ts`
- This helps identify partial buckets and actual data coverage within each bucket.
- Verified helper returns the new fields.
