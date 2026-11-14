# Implementation Plan: Click Ping Logging

**Branch**: `1-write-prd` | **Date**: 2026-11-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-click-ping-logging/spec.md`

## Summary

A single Python Worker serves three endpoints under `/api/v1/ping`. A POST records one row per
click in a D1 table and logs every request header. An OPTIONS request answers CORS preflight, and a
GET on `/health` reports liveness. FastAPI provides routing, a small middleware adds CORS headers,
and each operation that can fail has its own inline try/except that logs the step, error name, description, and source line.
D1 is reached through the `DB` binding. Preview and production
run the same code against separate databases. A GitHub Actions pipeline deploys to the shared
preview, smoke tests it, and only then deploys to production. Most scripts and the Cloudflare
config already exist. What remains is `src/worker.py` and the two GitHub files.

## Technical Context

**Language/Version**: Python 3.14 (`requires-python = ">=3.14"` in `pyproject.toml`, decided)

**Primary Dependencies**: FastAPI (`<0.163`), `python-multipart` (already listed, not needed by this feature); dev: `workers-py`, `workers-runtime-sdk`

**Storage**: Cloudflare D1, binding `DB`. Table `ping` from `schema.sql`. Databases `andexor-net-website-ping-prod` and `andexor-net-website-ping-prev`

**Testing**: No unit or functional tests (constitution VI, spec assumptions). End-to-end check is the preview smoke test and [quickstart.md](./quickstart.md)

**Target Platform**: Cloudflare Workers (Python Workers, `python_workers` compatibility flag)

**Project Type**: web-service (single Worker)

**Performance Goals**: Small-site click rate. Record stored within 5 seconds of the ping (SC-001). No capacity planning

**Constraints**: Response is 204 with no body on success. Never fail the visitor's navigation. No validation, auth, rate limiting, or retries

**Scale/Scope**: One table, three endpoints, one source file of roughly 100 lines

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How the plan satisfies it |
|---|---|---|
| I. Specifications Are the Source of Truth | Pass | The plan and contracts derive from `spec.md`. `PRD.md` is not consulted again |
| II. Standard Tooling | Pass | `uv`, `pywrangler` through `uv run`, `cf` for D1 and previews. No tokens in the repo |
| III. Nothing Reaches Production Untested | Pass | CI job order: preview deploy, health check, POST must return 204, then production. Separate databases |
| IV. Errors and Health | Pass | A try/except surrounds every operation that can fail (header logging, timestamp, D1 write, CORS handling). Each is written inline and logs the step name, error name, description, and source line, then returns 500 `{"ok": false}`. There is no catch-all handler, shared middleware, or logging helper. Health never touches D1 |
| V. Repeatable Scripts | Pass | `create_db.py`, `preview-create.sh`, `preview-delete.sh` are idempotent and read names from `wrangler.jsonc`. Manual steps are in `MANUAL-TASKS.md` |
| VI. Simplicity | Pass | No validation, auth, rate limiting, or tests. One source file |
| File conventions | Pass | SPDX header on every new file. Straight quotes. `wrangler.jsonc` stays plain JSON |

Post-design re-check: still passes. No complexity violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-click-ping-logging/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── http-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/
└── worker.py                  # to write: FastAPI app, CORS middleware, inline try/except around each fallible step, Worker entrypoint
schema.sql                     # exists
wrangler.jsonc                 # exists: route, DB binding, ALLOWED_ORIGINS, previews block
pyproject.toml                 # exists
scripts/
├── create_db.py               # exists
└── query_db.py                # exists
preview-create.sh              # exists
preview-delete.sh              # exists
preview-test.sh                # exists
health.sh, run.sh, deploy.sh   # exist
.github/
├── workflows/ci.yml           # to write: preview, smoke test, production
└── dependabot.yml             # to write: uv ecosystem
```

**Structure Decision**: One Worker module, `src/worker.py`, matching `main` in `wrangler.jsonc`.
The service is small enough that splitting it would add files without adding clarity.

## Complexity Tracking

No violations.
