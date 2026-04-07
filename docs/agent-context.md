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

## Milestone update: interview-readiness assessment for AI web developer roles
- Current objective: Reassess `esp32_api` as the primary portfolio project for AI web developer interview prep and identify the highest-value improvements for the next 3-5 days.
- What changed: Reviewed `README.md`, `server/app/main.py`, `server/app/api/rag_router.py`, `server/app/rag/deps.py`, `server/app/rag/rag_query.py`, `server/app/rag/rag_index.py`, and current dependency/test footprint. Confirmed the project already demonstrates a credible stack match: FastAPI backend, Supabase/Postgres, RAG endpoints, Ollama/LangChain/LlamaIndex usage, and planned UI integration. Also confirmed major readiness gaps: no visible automated tests, permissive CORS in `main.py`, unauthenticated `/rag/query` routes, secrets loaded loosely in `rag/deps.py`, and some README/run-command drift versus current app layout.
- Next step: Prioritize a short sprint focused on tests, security hardening, clearer architecture/demo docs, and a polished interview narrative around this codebase.
- Blockers/risks: Some improvements depend on local model/runtime availability (`Ollama`, Postgres/Supabase, env vars), so deliverables should emphasize code quality and explainable design even if full end-to-end deployment is not completed this week.
- Branch and latest commit hash: Branch/hash not checked in this pass.

## Milestone update: pre-interview prep list reframed
- Current objective: Reframe the prep plan around a canonical Planning -> Retrieval -> UI Execution workflow, cross-stack architectural translation, and enterprise Claude orchestration.
- What changed: Captured the need to explicitly discuss:
  - Planning/RAG Retrieval/UI Execution as the canonical workflow for AI web apps.
  - Common architectural patterns across Python/TypeScript and .NET/C#/Blazor, including dependency injection, middleware, typed contracts, async programming, and service boundaries.
  - When the codebase is operating in object-composition mode (framework objects, engines, services) versus functional mode (pure transforms, parsing, planning, normalization).
  - General Dynamics / GDIT-style mission use cases: AI sidecar services for legacy modernization, secure operator workflows, anomaly detection, summarization, retrieval over policy/standards, and human-in-the-loop execution.
  - Claude orchestration strategy: prefer a provider boundary that can use Anthropic directly or through Bedrock, while keeping app-level orchestration model-agnostic.
  - A likely repo cleanup direction: separate LangChain and LlamaIndex responsibilities into clearer provider/service layers instead of mixing them in `server/app/rag/deps.py`.
- Next step: Present the rewritten pre-interview checklist to the user and, if requested, convert it into implementation tasks against specific files.
- Blockers/risks: Public General Dynamics/GDIT use-case alignment is inferred from official public material and the recruiter description, not from a private job architecture document.
- Branch and latest commit hash: Branch/hash not checked in this pass.

## Milestone update: concrete 5-day prep sprint drafted
- Current objective: Convert the interview-prep themes into a time-boxed schedule with exact deliverables against `esp32_api`.
- What changed: Prepared a 5-day plan centered on: architecture and README cleanup, test coverage, security hardening, clearer LangChain/LlamaIndex separation, Claude/provider-boundary positioning, and interview rehearsal language tied to the repo's Planning -> Retrieval -> UI Execution flow.
- Next step: Share the detailed day-by-day plan with file targets and expected interview talking points.
- Blockers/risks: Time is limited, so the plan should prioritize defensible improvements over broad refactors or speculative framework churn.
- Branch and latest commit hash: Branch/hash not checked in this pass.

## Milestone update: README and architecture reframed around real UI split
- Current objective: Align `esp32_api` docs with the actual codebase and interview framing.
- What changed:
  - Updated `README.md` to reflect the real backend layout under `server/app/*`, corrected install/run commands, expanded endpoint coverage, and explicitly framed the backend around Planning -> Retrieval -> UI Execution.
  - Documented that `ui/` in this repo is only a placeholder scaffold and that the real UI execution layer is the separate `esp32_ui` project deployed at `https://esp32ui.vercel.app`.
  - Added `docs/architecture.md` with a system diagram, repo mapping, cross-stack translation notes, and enterprise positioning.
  - Captured the rationale that backend structure evolved in response to frontend-driven performance and API needs.
- Next step: Review the new docs for wording accuracy, then move to tests and security hardening.
- Blockers/risks: README now references the external `esp32_ui` deployment by convention; if the deployment URL or repo boundaries change later, docs should be updated to match.
- Branch and latest commit hash: `apr2026-sprint` @ `d0dc279`.

## Milestone update: cherry-pick conflict resolved onto main
- Current objective: Move the README/architecture cleanup commit from a separate branch onto `main`.
- What changed:
  - Resolved a cherry-pick conflict in `docs/agent-context.md` by keeping both the interview-prep milestone notes and the later README/architecture milestone note.
  - Continued the cherry-pick successfully, creating commit `0382172` on `main`.
  - Confirmed git status is now clean and `main` is ahead of `origin/main` by 1 commit.
- Next step: Push `main` when ready, then continue with the next documentation or testing task.
- Blockers/risks: None in the git state currently; the main remaining decision is when to push `main`.
- Branch and latest commit hash: `main` @ `0382172`.

## Milestone update: planning-retrieval-execution refactor scaffolding
- Current objective: Move the backend toward an explicit Planning -> Retrieval -> Execution architecture while preserving the current FastAPI app and existing LangChain/LlamaIndex integrations.
- What changed:
  - Completed the package split so current runtime code now lives under:
    - `server/app/planning/*` for query planning and agent workflow entry points
    - `server/app/retrieval/vector/*` for snapshot/doc/vector retrieval and indexing
    - `server/app/execution/answering/*` for answer synthesis
    - `server/app/frameworks/*` for LangChain and LlamaIndex runtime adapters
    - `server/app/providers/ollama/*` for provider-specific Ollama configuration
  - Added package roots for `frameworks` and `providers` so those boundaries are explicit importable modules rather than implicit namespace folders.
  - Fixed the last stale route import in `server/app/api/rag_router.py` so `/rag/ingest_docs` now imports from `app.retrieval.vector.ingest_docs`.
  - Updated `README.md` and `docs/architecture.md` to describe the new structure, clarify that `sql/` remains the shared low-level data-access layer, and keep the real UI execution boundary in the separate `esp32_ui` repo.
  - Verified import sanity from the active server venv for:
    - `app.main`
    - `app.api.rag_router`
    - `app.execution.answering.rag_query`
    - `app.frameworks.*`
    - `app.planning.*`
    - `app.providers.*`
    - `app.retrieval.vector.*`
- Next step: Continue the cleanup by deciding which future provider/framework slots should be documented only versus scaffolded in code, then add tests around the new planning and retrieval boundaries.
- Blockers/risks:
  - Corpus assets still live under `server/app/rag/docs/*`; that is intentional for now, but should eventually move to a less legacy-looking location if the ingestion pipeline settles.
  - There are still many uncommitted refactor changes on branch `cleanup`, so the next pass should be careful and incremental.
- Branch and latest commit hash: `cleanup` @ `d746247406e4370355e23a4a263d6dd0642ec6cb` (working tree dirty).

## Milestone update: structured retrieval moved under retrieval/
- Current objective: Finish the structured half of the retrieval architecture so timeseries, weather, and SQL-backed access live under `retrieval/` instead of being split across `api/` and `sql/`.
- What changed:
  - Added `server/app/retrieval/structured/sql_queries.py` and moved the live Supabase/psycopg data-access code there.
  - Added `server/app/retrieval/structured/timeseries.py` so `/timeseries` and `/timeseries/summary` route handlers are now thin HTTP wrappers over retrieval functions.
  - Added `server/app/retrieval/structured/weather.py` so `/weather/hourly` route logic now delegates to a structured retrieval layer while keeping provider-specific transport code in `server/app/weather/*`.
  - Added `server/app/retrieval/registry.py` to expose the current structured retrieval entry points from one place.
  - Added `server/app/retrieval/state/app_state.py` as a reserved state-retrieval boundary for future UI/system-state-aware planning, without forcing that feature into the current runtime yet.
  - Updated `server/app/main.py`, `server/app/api/timeseries_router.py`, `server/app/api/weather_router.py`, `README.md`, and `docs/architecture.md` to use and describe the new `retrieval/structured/*` layout.
  - Removed the old `server/app/sql/*` package after updating imports, per the repo preference to avoid compatibility wrappers around renamed/moved modules.
  - Verified import sanity from the active server venv for:
    - `app.main`
    - `app.api.timeseries_router`
    - `app.api.weather_router`
    - `app.retrieval.structured.sql_queries`
    - `app.retrieval.structured.timeseries`
    - `app.retrieval.structured.weather`
    - `app.retrieval.registry`
    - `app.retrieval.state.app_state`
- Next step: Decide whether to move corpus assets from `server/app/rag/docs/*` into a more neutral retrieval/corpus location, then add tests around the new structured retrieval functions rather than only around the routers.
- Blockers/risks:
  - `server/app/weather/*` is still intentionally separate because it currently behaves as a provider-adapter layer, but that may need clearer naming if more external providers are added.
  - The retrieval state boundary is intentionally minimal right now; it exists to match the target architecture, not because the backend currently persists frontend filter state.
- Branch and latest commit hash: `cleanup` @ `d746247406e4370355e23a4a263d6dd0642ec6cb` (working tree dirty).

## Milestone update: external adapters and corpus paths cleaned up
- Current objective: Remove the last legacy folder names so the tree reads like a reusable architecture rather than a weather-only or old-RAG-specific prototype.
- What changed:
  - Renamed `server/app/weather/*` to `server/app/external/*` so external API adapters are no longer weather-specific by name.
  - Moved the ingestion corpus from `server/app/rag/docs/*` to `server/app/retrieval/corpus/*`.
  - Updated live imports so:
    - `retrieval/structured/weather.py` now imports from `app.external.*`
    - `retrieval/vector/ingest_docs.py` now imports URLs and PDFs from `app.retrieval.corpus.*`
  - Added `server/app/retrieval/corpus/__init__.py` and updated docs (`README.md`, `docs/architecture.md`, `docs/2026-01-27-rag-setup-and-next-steps.md`) to reflect `external/` and `retrieval/corpus/`.
  - Removed obsolete directories `server/app/rag`, `server/app/scripts`, and `server/app/sql` after the code and assets were moved.
  - Verified import sanity for:
    - `app.main`
    - `app.api.weather_router`
    - `app.retrieval.structured.weather`
    - `app.retrieval.corpus.urls`
    - `app.external.weather_hourly`
    - `app.external.weather_open_meteo`
- Next step: Add tests around the new retrieval boundaries, and consider making `retrieval/vector/ingest_docs.py` load web content lazily instead of doing network work at import time.
- Blockers/risks:
  - `ingest_docs.py` still performs eager web-document loading at import time, which can hang or fail in restricted environments. The architecture is cleaner, but that module still needs a runtime-behavior cleanup.
  - Historical notes earlier in this file still mention the pre-rename `weather/` and `rag/docs/` paths; those are retained as history, not current architecture.
- Branch and latest commit hash: `cleanup` @ `d746247406e4370355e23a4a263d6dd0642ec6cb` (working tree dirty).

## Milestone update: ingest_docs made lazy-import safe
- Current objective: Remove eager network and file-loading work from `retrieval/vector/ingest_docs.py` so imports stay cheap and smoke tests do not hang on external fetches.
- What changed:
  - Reworked `server/app/retrieval/vector/ingest_docs.py` so PDF loading and web loading now happen through explicit helper functions:
    - `load_pdf_docs()`
    - `load_web_docs()`
    - `build_raw_docs()`
  - Removed module-level initialization of `pdf_docs`, `web_docs`, and `raw_docs`.
  - Updated `ingest()` to call `build_raw_docs()` at runtime instead of relying on import-time side effects.
  - Verified that `app.retrieval.vector.ingest_docs` now imports cleanly without performing web requests, and that the new helper functions are present.
- Next step: Add tests around the retrieval helpers and consider whether `load_web_docs()` should eventually support dependency injection or mocking hooks for easier offline testing.
- Blockers/risks:
  - `ingest()` still performs real network fetches when called, which is expected. The change here only removes eager side effects at import time.
- Branch and latest commit hash: `cleanup` @ `d746247406e4370355e23a4a263d6dd0642ec6cb` (working tree dirty).

## Milestone update: retrieval-focused pytest coverage added
- Current objective: Add meaningful automated tests around the new retrieval architecture so interview and production-readiness discussions are backed by real coverage.
- What changed:
  - Added `tests/conftest.py` to put `server/` on the pytest import path.
  - Added `tests/test_retrieval_timeseries.py` covering:
    - invalid table rejection
    - snapshot bucketing rejection
    - aggregated retrieval dispatch
    - raw row retrieval dispatch
    - summary rejection for snapshots
    - summary happy path
  - Added `tests/test_retrieval_weather.py` covering:
    - Open-Meteo dispatch
    - NOAA/default dispatch
  - Added `tests/test_ingest_docs.py` covering:
    - `build_raw_docs()` combination and metadata normalization
    - `clean_text()` normalization
    - `load_web_docs()` fallback path using mocked `requests`
  - Verified with:
    - `cd /workspaces/esp32_api/server && . .venv/bin/activate && python -m pytest /workspaces/esp32_api/tests/test_retrieval_timeseries.py /workspaces/esp32_api/tests/test_retrieval_weather.py /workspaces/esp32_api/tests/test_ingest_docs.py`
    - Result: `11 passed`
- Next step: Add API-layer tests for auth/header behavior and, if useful, unit tests around `planning/core/query_planner.py`.
- Blockers/risks:
  - Test run emitted third-party warnings from `pyiceberg` plus a pytest cache warning because this environment cannot write `.pytest_cache`; neither affected pass/fail.
- Branch and latest commit hash: `cleanup` @ `d746247406e4370355e23a4a263d6dd0642ec6cb` (working tree dirty).

## Milestone update: auth and planning tests added
- Current objective: Extend the new test coverage into security-sensitive auth helpers and the planning layer so the Planning -> Retrieval -> Execution story has automated checks at more than one boundary.
- What changed:
  - Added `tests/test_api_auth.py` covering:
    - `require_status_token`
    - `require_ingest_token`
    - `require_rag_token`
    for both rejection and acceptance paths.
  - Added `tests/test_query_planner.py` covering:
    - valid JSON planner output parsing
    - fallback behavior when the planner returns invalid JSON
    - absolute time-range resolution
    - day-part relative time-range resolution
  - Verified the full current test set with:
    - `cd /workspaces/esp32_api/server && . .venv/bin/activate && python -m pytest /workspaces/esp32_api/tests`
    - Result: `21 passed`
- Next step: If deeper API coverage is still desired, investigate why `fastapi.testclient.TestClient` requests with header-based auth dependencies hang in this environment before investing more time in route-level tests.
- Blockers/risks:
  - I initially attempted route-level auth tests with `TestClient`, but even a minimal FastAPI app using the auth dependency hung on requests in this environment. To keep momentum, auth coverage currently targets the dependency layer directly rather than full HTTP request/response tests.
  - Test run still emits third-party `pyiceberg` deprecation warnings plus a pytest cache warning due read-only cache writes; neither affected pass/fail.
- Branch and latest commit hash: `cleanup` @ `d746247406e4370355e23a4a263d6dd0642ec6cb` (working tree dirty).

## Milestone update: README testing section added
- Current objective: Make the new automated coverage visible in repo-facing documentation so reviewers can understand what is tested and how to run it.
- What changed:
  - Added a `Testing` section to `README.md`.
  - Documented the current coverage areas across auth, planning, structured retrieval, and ingestion helpers.
  - Added the exact pytest command for the server venv and recorded the current result as `21 passed`.
- Next step: Commit the cleanup branch in logical chunks and merge it back to `main`.
- Blockers/risks: README test count is a snapshot of the current branch; if tests change later, the count should be updated with them.
- Branch and latest commit hash: `cleanup` @ `d746247406e4370355e23a4a263d6dd0642ec6cb` (working tree dirty).
