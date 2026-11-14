---

description: "Task list for Capture More Request Headers"
---

# Tasks: Capture More Request Headers

**Input**: Design documents from `/specs/002-capture-request-headers/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-api.md, quickstart.md

**Tests**: None. The constitution (Principle VI) and the spec exclude unit and functional tests. Each
story is verified with the matching [quickstart.md](./quickstart.md) scenario instead.

**Organization**: Tasks are grouped by user story. The migration comes first, because it is a
prerequisite for storing the new columns even though its story (US3) has a lower priority. All
Worker code is in `src/worker.py`, so Worker tasks run in order and none are marked [P].

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 to US3)

## Rules for every task that writes Worker code

These come from constitution Principle IV and the base spec's research R5. Do not skip them.

- Every statement that can raise an error stays inside its own inline `try/except`. The new code
  goes inside the existing `log_headers` and `db_insert` blocks. Do not add a helper function, shared
  middleware, or `exception_handler` that does the error logging.
- Each `except` keeps writing one log line:
  `ping_error step=<step> error=<ErrorName>: <description> line=<n>` with
  `n = e.__traceback__.tb_lineno`, then returns HTTP 500 with `{"ok": false}`.
- The SQL text is built only from the `STORED_HEADERS` constant. Request data is never put into the
  SQL text. Every value is a bound parameter. A missing header is passed as `jsnull`.
- Straight quotes only. SPDX header on every new file.

---

## Phase 1: Setup

- [X] T001 Confirm the working branch is `4-capture-request-headers`, the six column names in `specs/002-capture-request-headers/data-model.md` match the spec's FR-001, and `uv sync` succeeds.

---

## Phase 2: Foundational (blocks every story)

**Purpose**: The full table definition and the migration for databases that already exist.

- [X] T002 In `schema.sql`, change the `CREATE TABLE IF NOT EXISTS ping` statement to the full table: after `ping_to` add `cf_connecting_ip TEXT`, `cf_ipcountry TEXT`, `cf_ray TEXT`, `host TEXT`, `user_agent TEXT`, `x_real_ip TEXT`, all nullable. Leave the four `CREATE INDEX IF NOT EXISTS` statements exactly as they are and add no index for the new columns (FR-004). Keep each statement on its own lines and put no `--` inside a statement.
- [X] T003 Create `scripts/migrate_db.py` with the SPDX header, copied from `scripts/query_db.py`, and a docstring with the usage `uv run scripts/migrate_db.py [--preview]`. It reads `wrangler.jsonc` (`d1_databases[0]` for production, `previews.d1_databases[0]` with `--preview`), runs `PRAGMA table_info(ping)` through `cf d1 query <database_id> --sql ...` with `subprocess`, takes the column names from `results`, then runs `ALTER TABLE ping ADD COLUMN <name> TEXT` for each of the six new columns that is missing, one statement each. It prints the columns it added, or that none were needed. It never drops or changes data, exits non-zero with a clear message if `cf` fails, and is safe to run more than once (FR-008). Handle the real output shape of `cf d1 query`, an array of statement results (base research R10).
- [X] T004 Run `uv run scripts/migrate_db.py --preview`. Confirm it reports the six columns added. Run it again and confirm it adds nothing. Run `uv run scripts/query_db.py --preview` and confirm the existing rows are unchanged with the six new fields null. Run `cf d1 query <preview id> --sql "SELECT name FROM sqlite_master WHERE type='index'"` and confirm the same four `idx_ping_*` indexes and no new one. Run `./preview-test.sh` once before any redeploy, to confirm the old Worker still returns 204 against the migrated database (do not deploy yet if it fails). Record the confirmed `PRAGMA` output shape and the working `ALTER TABLE` call in `specs/002-capture-request-headers/research.md` R1.

**Checkpoint**: The preview database has the six columns, the migration is repeatable, and the old Worker still works against it.

---

## Phase 3: User Story 1 - Store more details about each click (Priority: P1) - MVP

**Goal**: A ping stores the six new headers in the new columns, NULL when absent.

**Independent Test**: quickstart scenarios 3 and 4. A POST with `X-Real-IP` and `User-Agent` stores them, and a bare POST stores NULL for `x_real_ip`.

- [X] T005 [US1] In `src/worker.py`, add a module constant `STORED_HEADERS`, an ordered tuple of `(header name, column name)` pairs for all nine stored headers, lower-case header names: `referer`/`referer`, `ping-from`/`ping_from`, `ping-to`/`ping_to`, `cf-connecting-ip`/`cf_connecting_ip`, `cf-ipcountry`/`cf_ipcountry`, `cf-ray`/`cf_ray`, `host`/`host`, `user-agent`/`user_agent`, `x-real-ip`/`x_real_ip`. Put a short comment above it saying that storing and logging are both derived from it.
- [X] T006 [US1] In `src/worker.py`, inside the existing `db_insert` try/except, build the INSERT from `STORED_HEADERS`: the column list is `received_at` followed by the column names, one `?` per value, and the bound values are `received_at` followed by each header value from `headers.get(name)`, with `jsnull` for `None`. Remove the three separate `referer`, `ping_from`, `ping_to` variables. Quote these data-model rules in a comment or keep them satisfied: "A header that is absent is stored as NULL", "A header that is present is stored exactly as received, with no trimming or validation", "Identical rows are allowed".
- [X] T007 [US1] Deploy with `uv run pywrangler preview --name preview` and run quickstart scenarios 3 and 4 on the preview. Confirm which of the six headers Cloudflare actually sends (`x-real-ip` may be absent) and record it in `specs/002-capture-request-headers/research.md` R3. Confirm a second identical POST creates a second row and `./preview-test.sh` still returns 204.

**Checkpoint**: User Story 1 works on its own. This is the MVP.

---

## Phase 4: User Story 2 - Log only what is stored (Priority: P1)

**Goal**: The log line holds only the nine stored headers.

**Independent Test**: quickstart scenario 5. A ping with `Cookie`, `Authorization`, and an unlisted header leaves none of them in the log.

- [X] T008 [US2] In `src/worker.py`, inside the existing `log_headers` try/except, replace logging the whole `headers` dict with a JSON object holding only the stored headers that are present: `{name: headers[name] for name, _ in STORED_HEADERS if name in headers}`, written with `json.dumps(..., ensure_ascii=False)` so no escape characters are added (FR-005, FR-006). Do not name `Cookie`, `Authorization`, or any other header to exclude. Keep `read_headers` as it is.
- [ ] T009 [US2] Deploy the preview and run quickstart scenario 5. The owner reads the Workers Logs in the Cloudflare dashboard, because the log cannot be read from here. Ask the owner to confirm that the line for that ping holds the stored headers and no `Cookie`, `Authorization`, or `x-made-up`. Record the result in `specs/002-capture-request-headers/research.md` R2.

**Checkpoint**: Storing and logging both follow `STORED_HEADERS`.

---

## Phase 5: User Story 3 - Add the new fields to existing data stores (Priority: P2)

**Goal**: Existing and new databases both end with the full table, and production is migrated before the merge.

**Independent Test**: quickstart scenarios 1, 2, 7 and 8.

- [X] T010 [US3] Verify the new-database path without touching preview: create a throwaway D1 database with `cf d1 create`, apply `schema.sql` to it with `cf d1 query`, confirm the `ping` table has all eleven columns and the same four indexes, then delete the throwaway database. Change quickstart scenario 7 in `specs/002-capture-request-headers/quickstart.md` to describe this check, since a preview delete and recreate would change the preview database id in `wrangler.jsonc`.
- [X] T011 [US3] In `MANUAL-TASKS.md`, add a section for this feature: before opening the PR run `uv run scripts/migrate_db.py --preview`, and before merging run `uv run scripts/migrate_db.py` for production. Say that the order matters, that the migration only adds nullable columns so the Worker currently in production keeps working in between, and that CI cannot run it because its token has no D1 permission.
- [ ] T012 [US3] Owner checkpoint: the owner runs `uv run scripts/migrate_db.py` against production before merging, then confirms it reported the six columns added. This task is the owner's. Do not run it against production without the owner's go-ahead.

---

## Phase 6: Polish and cross-cutting

- [X] T013 [P] Update the base specification in `specs/001-click-ping-logging/` as listed in "Changes to the base specification" in `specs/002-capture-request-headers/spec.md`: FR-005 (new columns not indexed), FR-006 and User Story 1 scenario 4 (log only stored headers), the first assumption (the log-everything decision is ended), and the `Ping record` entity. Mirror the changes in its `data-model.md` and `contracts/http-api.md`, and its `quickstart.md` scenario 4.
- [X] T014 [P] Make the docs match: `CLAUDE.md` (the POST line says it logs all request headers, and the table line says all columns are indexed), `CICD.md` (the Logs section says the full set of request headers is logged), `setup.md` (add the migration step for existing databases), and `README.md` if its text no longer fits.
- [ ] T015 Final checks: grep every new or changed file for typographic quotes, confirm the SPDX header on `scripts/migrate_db.py`, confirm `src/worker.py` has no header name literal for `Cookie` or `Authorization`, and run quickstart scenarios 1 to 5 once end to end on the preview.
- [ ] T016 After the PR is merged and the production deploy has run, confirm `curl -si https://andexor.net/api/v1/ping/health` returns 200 with `{"ok": true}`. Do not POST to production.

---

## Dependencies and order

- T001, then T002 and T003 (different files, can run together), then T004.
- T005, T006, T008 all edit `src/worker.py` and run in order. T007 and T009 deploy the preview after them.
- T004 must be done before T007, because the preview database needs the new columns before the new Worker is deployed.
- T012 must be done before the PR is merged.
- T013 and T014 can run together and at any time after T006 and T008.
- T016 comes last, after the merge.

## Implementation strategy

1. MVP: T001 to T007. The new columns are stored.
2. Add US2 (T008, T009), so that the log stops holding every header. This is the privacy fix and should ship with the MVP in the same PR.
3. Finish US3 (T010 to T012), the docs (T013, T014), and the final checks (T015).
4. Open one PR. After it is green and the owner has run the production migration (T012), merge, then T016.
