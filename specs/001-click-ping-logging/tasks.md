---

description: "Task list for Click Ping Logging"
---

# Tasks: Click Ping Logging

**Input**: Design documents from `/specs/001-click-ping-logging/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-api.md, quickstart.md

**Tests**: None. The constitution (Principle VI) and the spec exclude unit and functional tests. Each
story is verified with the matching [quickstart.md](./quickstart.md) scenario instead.

**Organization**: Tasks are grouped by user story. All Worker code is in one file, `src/worker.py`,
so Worker tasks run in order and none are marked [P].

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 to US5)

## Rules for every task that writes Worker code

These come from constitution Principle IV and research R5. Do not skip them.

- Every statement that can raise an error gets its own inline `try/except` at that spot.
- No helper function, shared middleware, or `exception_handler` may do the error logging.
- Each `except` writes one log line: `ping_error step=<step> error=<ErrorName>: <description> line=<n>`,
  where `<n>` is `e.__traceback__.tb_lineno`, and returns HTTP 500 with `{"ok": false}`.
- Each step name is unique in the file. The step names are listed in T018.
- The file keeps the SPDX header, straight quotes only.

## Phase 1: Setup

**Purpose**: Confirm the existing scaffolding before writing code

- [X] T001 Confirm `wrangler.jsonc` has `main` = `src/worker.py`, the route `andexor.net/api/v1/ping*`, the `DB` binding, and `ALLOWED_ORIGINS` in both `vars` and `previews.vars`. Fix any mismatch, keeping the file plain JSON.
- [X] T002 Run `uv sync` and confirm it resolves with Python 3.14 (`requires-python = ">=3.14"` in `pyproject.toml`). Python 3.14 is confirmed to work on Python Workers, because `andexor-net-website-contact-us` uses it.

---

## Phase 2: Foundational (blocking)

**Purpose**: A runnable Worker skeleton, and answers to the two open VERIFY items in research.md

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create `src/worker.py` with the SPDX header, a FastAPI `app`, and the entrypoint `Default = asgi.entrypoint(app)` (research R2). Read `ALLOWED_ORIGINS` from the Worker env inside its own inline try/except with step `read_config`.
- [ ] T004 **Owner action, stop here.** Ask the owner to complete all of `MANUAL-TASKS.md` Step 1 now: it includes creating the preview Worker, which needs `src/worker.py` from T003. Claude must not create the preview Worker or run the pipeline to create it. Do not start T006 until the owner confirms Step 1 is done.
- [ ] T005 After T004, run `uv run scripts/create_db.py` a second time and confirm it reports the database and `database_id` already exist and changes nothing. Run `uv run scripts/query_db.py --preview` and confirm it prints one JSON array of rows (the spec for the script). If the real `cf d1 query` output has a different shape, fix `scripts/query_db.py` to print only the rows, and record the real shape in `specs/001-click-ping-logging/research.md`.
- [ ] T006 In `src/worker.py`, add a throwaway route that reads the D1 binding as `request.scope["env"].DB` and runs `SELECT 1 FROM ping`. Deploy it with `uv run pywrangler preview --name preview` and call it on the preview URL (the preview database already has the `ping` table from MANUAL-TASKS Step 1, and there is no local D1 to set up). If the binding is not reachable, switch to the `WorkerEntrypoint` class form with `await asgi.fetch(app, request, self.env)`. Record the working form in `specs/001-click-ping-logging/research.md` R2 and remove the throwaway route.
- [ ] T007 In `src/worker.py`, find the call that passes an explicit JS `null` to `.bind()` for a missing value (for example `js.null`) and confirm D1 stores NULL, per research R3. Test it on the preview, using a throwaway route that inserts a row with a null value, and check the row with `uv run scripts/query_db.py --preview`. Delete the throwaway route and test row afterwards. Record the working call in `specs/001-click-ping-logging/research.md` R3.

**Checkpoint**: The owner has done Step 1, the existing scripts are verified, the DB binding is reachable, and NULL handling is settled.

---

## Phase 3: User Story 1 - Record a link click (Priority: P1) - MVP

**Goal**: A ping to `POST /api/v1/ping` returns 204 and stores one row. All request headers are logged.

**Independent Test**: quickstart scenarios 1, 3 and 4. One POST with `Referer`, `Ping-From`, `Ping-To` gives 204 with no body, one new row with all four fields filled, and one log line holding every header.

- [ ] T008 [US1] In `src/worker.py`, add `POST /api/v1/ping` returning HTTP 204 with an empty body. Any request body is ignored.
- [ ] T009 [US1] In `src/worker.py`, in the POST handler, read the request headers and write them to the log as one JSON line, `json.dumps(dict(request.headers), ensure_ascii=False)`, so no escape characters are added (FR-006). Use two separate inline try/except blocks: `read_headers` and `log_headers`.
- [ ] T010 [US1] In `src/worker.py`, build `received_at` as the current UTC time in ISO 8601 with milliseconds and a `Z` suffix (research R7), inside its own inline try/except with step `make_timestamp`. The caller can never supply it.
- [ ] T011 [US1] In `src/worker.py`, insert the row with `INSERT INTO ping (received_at, referer, ping_from, ping_to) VALUES (?, ?, ?, ?)` using bound parameters only, inside its own inline try/except with step `db_insert`. Data-model rules, quoted verbatim: "A header that is absent is stored as NULL", "A header that is present is stored exactly as received, with no trimming or validation", and "Identical rows are allowed". A missing header or a `None` value MUST be passed as an explicit JS `null` (T007).
- [ ] T012 [US1] Apply `schema.sql` to the preview database with `./preview-create.sh`, deploy with `uv run pywrangler preview --name preview`, and run quickstart scenarios 1, 3 and 4. Confirm a second identical POST creates a second row and a POST with no `Ping-*` headers stores NULLs.

**Checkpoint**: User Story 1 works on its own. This is the MVP.

---

## Phase 4: User Story 2 - CORS (Priority: P2)

**Goal**: Browsers may send pings from `https://andexor.net` and `http://localhost:8787`.

**Independent Test**: quickstart scenario 5. A preflight from the website origin gets 204 with that origin echoed. An unlisted origin gets the first listed origin.

- [ ] T013 [US2] In `src/worker.py`, add `OPTIONS /api/v1/ping` returning HTTP 204 with no body (FR-007).
- [ ] T014 [US2] In `src/worker.py`, add a middleware that sets CORS headers on every response (research R4, not `CORSMiddleware`): `Access-Control-Allow-Origin` is the request `Origin` if it is in `ALLOWED_ORIGINS`, otherwise the first entry; `Access-Control-Allow-Methods: POST, OPTIONS`; `Access-Control-Allow-Headers: Content-Type`; `Vary: Origin`. The origin matching and header setting are in their own inline try/except with step `cors_origin`. The middleware does not log errors for other steps.
- [ ] T015 [US2] Run quickstart scenario 5 against the preview and confirm the echoed origin, the fallback origin, and the `Vary: Origin` header.

---

## Phase 5: User Story 3 - Health (Priority: P2)

**Goal**: `GET /api/v1/ping/health` shows the service is alive.

**Independent Test**: quickstart scenario 2. 200 with `{"ok": true}`, even when the database is unavailable.

- [ ] T016 [US3] In `src/worker.py`, add `GET /api/v1/ping/health` returning 200 with `{"ok": true}`. It MUST NOT touch D1 or any other dependency (FR-010), so it has no database code and needs no try/except.
- [ ] T017 [US3] Run quickstart scenario 2 against the preview. Confirm the handler contains no database call.

---

## Phase 6: User Story 4 - Failures are logged with their location (Priority: P2)

**Goal**: A failure is logged with its step, error and line, and the caller learns only `{"ok": false}`.

**Independent Test**: quickstart scenario 6. A forced insert failure returns 500 with `{"ok": false}` and one log line naming `db_insert` and its line.

- [ ] T018 [US4] In `src/worker.py`, audit the whole file: every statement that can raise is inside its own inline try/except with a unique step name, each `except` logs `ping_error step=<step> error=<ErrorName>: <description> line=<n>` and returns 500 `{"ok": false}`, and there is no catch-all, shared helper, or `exception_handler`. Step names: `read_config`, `read_headers`, `log_headers`, `make_timestamp`, `db_insert`, `cors_origin`. Add any step that is missing.
- [ ] T019 [US4] In `specs/001-click-ping-logging/contracts/http-api.md`, list the step names from T018 under "Error logging", each with the code it guards.
- [ ] T020 [US4] Run quickstart scenario 6 on the preview: rename the table in the insert, redeploy, POST, and confirm a 500 with `{"ok": false}` and a `db_insert` log line with the correct line number. Then force a second, different failure in another step and confirm its log line shows a different step and line. Revert both.

---

## Phase 7: User Story 5 - Preview before production (Priority: P3)

**Goal**: A change reaches production only after the preview health check and test POST pass.

**Independent Test**: quickstart scenarios 7 and 8.

- [X] T021 [P] [US5] Create `.github/workflows/ci.yml` per `CICD.md` section 1: trigger on `pull_request` and `push` to `main`; job `Preview and smoke test` installs Node, uv and dependencies, runs `uv run pywrangler preview --name preview`, health-checks `GET /api/v1/ping/health` with 10 tries 3 seconds apart, and POSTs `/api/v1/ping` once with test `Referer`, `Ping-From` and `Ping-To` headers, failing unless the status is exactly 204 and never retrying; job `Deploy to production` has `needs`, runs only on push to `main`, runs `uv run pywrangler deploy`, then a GET-only health check on `https://andexor.net/api/v1/ping/health`. Use a job-level `concurrency` group `preview-environment` with no cancelling, `PREVIEW_NAME=preview`, secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, and action versions pinned and at least a week old. Add the SPDX header.
- [X] T022 [P] [US5] Create `.github/dependabot.yml` with the `uv` ecosystem enabled (CICD.md "Dependabot"). Add the SPDX header.
- [ ] T023 [US5] After the owner completes `MANUAL-TASKS.md` Step 2, run quickstart scenarios 7 and 8: confirm no test rows in the production database, run the negative test, and record the throwaway PR number in `CICD.md` section 4.

---

## Phase 8: Polish

- [ ] T024 [P] Update `CLAUDE.md` Status and CI lines to match what now exists, and `README.md` if the commands changed.
- [ ] T025 [P] Change the VERIFY items in `specs/001-click-ping-logging/research.md` (R2, R3, R8) to their confirmed results.
- [ ] T026 After asking the owner to confirm (it deletes preview data only), run `./preview-delete.sh` and then `./preview-create.sh` and the manual preview Worker step from `MANUAL-TASKS.md`, to prove the teardown and rebuild both work. Confirm `./preview-delete.sh` refuses to touch the production database.
- [ ] T027 Final checks: grep every new or changed file for typographic quotes, confirm the SPDX header on `src/worker.py`, `.github/workflows/ci.yml` and `.github/dependabot.yml`, and run all quickstart scenarios once end to end.

---

## Dependencies and Order

- Phase 1, then Phase 2, block everything else. T004 is an owner action that must finish before T006.
- US1 (Phase 3) has no story dependencies and is the MVP.
- US2 and US3 depend only on Phase 2. They can follow US1 in either order, but they edit `src/worker.py`, so they are done one at a time.
- US4 (Phase 6) audits the code from US1 and US2, so it runs after them.
- US5 `.github` files (T021, T022) do not depend on the Worker code and can be written in parallel with any phase, but T023 needs the Worker and the owner's manual Step 2.
- Polish runs last.

### Parallel opportunities

- T021 and T022 (different files).
- T024 and T025 (different files).
- T021/T022 alongside Phases 3 to 6.

## Implementation Strategy

- **MVP**: Phases 1, 2 and 3. After T012, a deployed preview records clicks.
- **Then**: US2 and US3 so the real website and the pipeline can use it, then US4, then US5.
- Deploy to preview after each phase and run the matching quickstart scenario before moving on.
