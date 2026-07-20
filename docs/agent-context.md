# Agent Context

## Last Updated
- 2026-07-20

## Workspace Scope
- Multi-root workspace covering `esp32_api`, `esp32_ui`, and `b2b-dashboard-demo`.
- Use this file for dynamic task/session context and handoff notes.
- Use workspace or repo settings for stable editor/runtime configuration.

## Current Objective
- Migrate `device/` from the AM2320 MicroPython prototype to PlatformIO firmware for an indoor ESP32-S3-DevKitC-1-N8R8 monitor.
- Add the BME280 and INMP441 sensor paths now that USB bootstrap and OTA are verified.

## Current Device Work
- Target: Espressif ESP32-S3-DevKitC-1 with ESP32-S3-WROOM-1-N8R8 (8 MB flash, 8 MB octal PSRAM).
- Planned wiring: BME280 SDA/SCL on GPIO10/9; INMP441 BCLK/WS/SD on GPIO17/18/21.
- OTA hostname: `indoor-sky.local`.
- PlatformIO USB and OTA environments are under `device/`.
- Existing ignored `device/secrets.py` supplies Wi-Fi credentials at build time without copying them into tracked source.
- Bootstrap firmware was installed successfully over native USB at `/dev/cu.usbmodem11201`.
- Bootstrap is online at `192.168.0.32`; `/status` confirms clean firmware identity, strong Wi-Fi, 8 MB PSRAM, and OTA readiness.
- macOS currently times out resolving `indoor-sky.local`, although the device advertises the name; OTA can target the IP directly.
- `/status` verifies `wifi_sleep: false`; loss improved to zero, but the extender path remains bursty at roughly 331 ms average latency.
- OTA negotiates and transfers normally, but the stock Espressif uploader aborts whenever one 1 KB acknowledgment exceeds its hard-coded 10-second limit. `device/scripts/espota.py` is the upstream uploader with that per-chunk timeout changed to the configured value; the OTA environment selects it through `use_local_espota.py`.
- The local uploader revealed the matching device-side limit: ArduinoOTA defaults to a one-second receive timeout with only three retries. Firmware now sets a 30-second receive timeout so transient extender stalls do not abort the update server.
- OTA was verified end to end on 2026-07-20 by wirelessly reinstalling clean firmware `1714178`; PlatformIO reported success and `/status` confirmed a reboot into the freshly built image. Use the explicit IP while mDNS remains unreliable on the extender network.

## Repository Map
- `esp32_api`: Python/FastAPI backend.
- `esp32_ui`: Next.js/React/TypeScript frontend.
- `b2b-dashboard-demo`: Separate Next.js/React/TypeScript frontend.

## Relevant Setup Notes
- `esp32_api` uses a local virtual environment at `.venv`.
- The backend interpreter is pinned in `esp32_api/.vscode/settings.json` with:
  - `python.defaultInterpreterPath: ${workspaceFolder}/.venv/bin/python`
  - `python.terminal.activateEnvironment: true`
- For the saved multi-root workspace, the interpreter setting should live in the `.code-workspace` file with the `esp32_api` folder-specific path.

## Frontend Notes
- `esp32_ui` and `b2b-dashboard-demo` are both standard Node/Next.js projects.
- Both advertise Node `>=20` and use TypeScript plus ESLint.
- These repos normally do not need special interpreter-style workspace settings.
- If VS Code ever misidentifies the frontend tooling in a multi-root session, add workspace-level overrides only then, such as `typescript.tsdk` or `eslint.workingDirectories`.

## Practical Guidance
- Prefer keeping workspace settings minimal.
- Pin the Python interpreter for `esp32_api`.
- Let VS Code auto-detect the TypeScript and ESLint tooling for the two frontend repos unless a concrete editor issue appears.
- Keep notes short and specific to what changed, what is next, and any blockers.

## Handoff Format
- When leaving context for the next session, record:
  - What changed
  - What is next
  - Any blockers or risks
  - Any repo-specific paths or settings that matter

## Source Context
- This workspace file was distilled from the continuity pattern used in the `orcasound-next` `docs/agent-context.md` file, but only the parts relevant to this workspace were retained.
