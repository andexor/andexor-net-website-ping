# Implementation Plan: Capture More Request Headers

**Branch**: `4-capture-request-headers` | **Date**: 2026-11-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-capture-request-headers/spec.md` (GitHub issue #4)

## Summary

The base service (`specs/001-click-ping-logging/`) is built and deployed. This feature adds six
nullable columns to the `ping` table and fills them from six more request headers. It also changes
the header log: instead of every request header, the log line holds only the headers that are
stored. One constant in `src/worker.py` lists the stored headers and their columns, and both the
INSERT and the log line are derived from it, so they cannot drift apart and every other header is
excluded without being named. A new idempotent script, `scripts/migrate_db.py`, adds the missing
columns to an existing preview or production database. `schema.sql` describes the full table for new
databases. No indexes are added for the new columns.

## Technical Context

**Language/Version**: Python 3.14 (unchanged)

**Primary Dependencies**: FastAPI (`<0.163`) (unchanged). No new dependencies

**Storage**: Cloudflare D1, binding `DB`. Table `ping` gains six TEXT columns. Databases `andexor-net-website-ping-prod` and `andexor-net-website-ping-prev`

**Testing**: No unit or functional tests (constitution VI). Verification is the preview smoke test and [quickstart.md](./quickstart.md)

**Target Platform**: Cloudflare Workers (Python Workers)

**Project Type**: web-service (single Worker)

**Performance Goals**: Unchanged. One INSERT per ping, now with 9 bound values instead of 4

**Constraints**: Response stays 204 with no body. Existing records must survive the schema change. The previous Worker version must keep working against a migrated database (columns are only added). The CI token has no D1 permission, so the migration cannot run in CI

**Scale/Scope**: One table, one source file changed, one new script

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How the plan satisfies it |
|---|---|---|
| I. Specifications Are the Source of Truth | Pass | This plan derives from `spec.md`. The same pull request updates the base spec items listed at the end of `spec.md`, and `README.md`, `setup.md`, `CICD.md`, `CLAUDE.md` stay consistent |
| II. Standard Tooling | Pass | The migration script uses `cf d1 query` through `subprocess`, like `create_db.py`. No tokens in the repo |
| III. Nothing Reaches Production Untested | Pass | The pipeline is unchanged. The migration runs on preview first, then on production before the merge. Preview and production keep separate databases |
| IV. Errors and Health | Pass | Header filtering, SQL building, and the INSERT sit inside the existing inline try/except steps (`log_headers`, `db_insert`). No helper, shared handler, or new catch-all. Health is untouched |
| V. Repeatable Scripts | Pass | `migrate_db.py` is idempotent, reads database names and ids from `wrangler.jsonc`, and only adds columns. The manual run is listed in `MANUAL-TASKS.md` |
| VI. Simplicity | Pass | No validation, auth, rate limiting, or tests. No indexes on the new columns |
| File conventions | Pass | SPDX header on `scripts/migrate_db.py`. Straight quotes. `wrangler.jsonc` unchanged |

Post-design re-check: still passes. No complexity violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-capture-request-headers/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── http-api.md          # only what changes from the base contract
├── checklists/
│   └── requirements.md
└── tasks.md                 # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/worker.py                 # change: STORED_HEADERS constant, log and INSERT derived from it
schema.sql                    # change: full table with the six new columns, indexes unchanged
scripts/migrate_db.py         # new: add missing columns to an existing database (--preview for preview)
scripts/query_db.py           # unchanged: SELECT * already prints the new columns
MANUAL-TASKS.md               # change: run migrate_db.py on preview before the PR, on production before the merge
README.md, setup.md, CICD.md, CLAUDE.md
specs/001-click-ping-logging/ # change: the amended items listed in the new spec
```

## Design Decisions

1. **One constant drives storage and logging.** `STORED_HEADERS` is an ordered tuple of
   `(header name, column name)` pairs for the nine stored headers. In the POST handler the log
   object is `{name: headers[name] for name, _ in STORED_HEADERS if name in headers}` (inside the
   `log_headers` step) and the INSERT column list and values come from the same tuple (inside the
   `db_insert` step). Nothing refers to `Cookie` or `Authorization`, so they are excluded
   implicitly (FR-005, FR-006). The SQL text is built only from the constant, never from request
   data, and all values stay bound parameters.
2. **Existing step names stay.** `read_headers`, `log_headers`, `make_timestamp`, and `db_insert`
   keep their meaning, so the error contract does not change (FR-009).
3. **Migration is a script, not code in the Worker.** SQLite has no `ADD COLUMN IF NOT EXISTS`, so
   `scripts/migrate_db.py` reads `PRAGMA table_info(ping)`, then runs `ALTER TABLE ping ADD COLUMN
   <name> TEXT` for each missing column. A second run finds nothing missing and changes nothing
   (FR-008, SC-003). It never drops or rewrites data.
4. **`schema.sql` is the full table.** New databases created by `create_db.py` or
   `preview-create.sh` get all eleven columns from the first statement, and the migration script is
   then a no-op. The four existing indexes stay and no new ones are added (FR-004, FR-007).
5. **Deployment order.** Migrate preview, open the PR (the preview deploy then works), migrate
   production, merge. Because the change only adds nullable columns, the Worker version currently in
   production keeps working in between.
6. **Log keys are lower-case header names**, and a header that is absent from the request is
   omitted from the log object (spec assumptions).

## Complexity Tracking

No violations.
