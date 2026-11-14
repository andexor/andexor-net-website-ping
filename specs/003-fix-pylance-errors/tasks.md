---

description: "Task list for Fix Pylance Type Errors"
---

# Tasks: Fix Pylance Type Errors

**Input**: Design documents from `/specs/003-fix-pylance-errors/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: None. The constitution (Principle VI) excludes unit tests. Each story is verified with the
matching [quickstart.md](./quickstart.md) scenario instead.

**Organization**: Both user stories are served by edits to one file, `src/worker.py`, so no task is
marked [P] and tasks run in order. US1 is the type fixes. US2 is proving behavior did not change.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Rules for every task that edits Worker code

- Every statement that can raise an error stays inside its own inline `try/except`. Do not add a
  helper function, shared middleware, or `exception_handler` that does the error logging
  (constitution Principle IV).
- Do not add `# type: ignore`, `# pyright:` comments, `cast`, `Any`, or any change to the checker
  settings (FR-006). No new dependency (FR-007).
- Responses, status codes, CORS headers, and stored data stay exactly as they are.
- Straight quotes only.

---

## Phase 1: Setup

- [X] T001 Record the baseline: run the editor diagnostics for `src/worker.py` and confirm 20 errors, so the fix can be compared against it

---

## Phase 2: User Story 1 - Open the service source with no reported problems (Priority: P1)

**Goal**: 0 problems reported for `src/worker.py`.

**Independent Test**: Quickstart step 1 and step 6.

- [X] T002 [US1] In `src/worker.py`, import `Awaitable` and `Callable` from `collections.abc`, then annotate `call_next` as `Callable[[Request], Awaitable[Response]]` and the return type as `Response` on both middleware functions, `load_config` and `cors` (research R1)
- [X] T003 [US1] In `src/worker.py`, in the `except` block of `load_config` (step `read_config`), replace `line={e.__traceback__.tb_lineno}` with an inline `line = f" line={e.__traceback__.tb_lineno}" if e.__traceback__ else ""` and write `{e}{line}` in the log message, so no `line=` part is logged when there is no traceback (research R2)
- [X] T004 [US1] In `src/worker.py`, make the same change in the `except` block of `cors` (step `cors_origin`)
- [X] T005 [US1] In `src/worker.py`, make the same change in the four `except` blocks of `ping` (steps `read_headers`, `log_headers`, `make_timestamp`, `db_insert`)
- [X] T006 [US1] Run the editor diagnostics for `src/worker.py` and confirm 0 errors and 0 warnings. If any remain, fix them without suppressions, then grep for `type: ignore` and `pyright:` and confirm none

**Checkpoint**: the Problems panel is empty for `src/worker.py`.

---

## Phase 3: User Story 2 - Behavior stays exactly the same (Priority: P1)

**Goal**: The service responds and logs as before.

**Independent Test**: Quickstart steps 2 to 5.

- [X] T007 [US2] Run `./run.sh`, POST to `/api/v1/ping`, and confirm 204 with no body and the same CORS headers as before (quickstart step 2)
- [X] T008 [US2] Run `./preview-test.sh` and confirm the health check and the test ping pass (quickstart step 3)
- [X] T009 [US2] Temporarily force a failure in each of the six steps (`read_config`, `read_headers`, `log_headers`, `make_timestamp`, `db_insert`, `cors_origin`) and confirm the log line is `ping_error step=<step> error=<ErrorName>: <description> line=<n>` and the response is 500 with `{"ok": false}`. Remove every forced failure afterwards and confirm with `git diff` that none remains (quickstart step 4)
- [X] T010 [US2] Confirm the no-traceback path: the log line ends after the description with no `line=` part, and the 500 response is still returned (quickstart step 5)

---

## Phase 4: Polish

- [X] T011 Check `README.md`, `setup.md`, and `CICD.md` for any mention of the log line format and keep them consistent with the spec (the format is unchanged when a traceback exists)
- [X] T012 Search the changed and new files for typographic quotes and confirm none
- [ ] T013 Commit on branch `7-fix-pylance-errors`, push, and open a PR that closes #7 with `--assignee ejenkins` and a review request to `andexor/write`

---

## Dependencies

- T001 first. T002 to T005 in order (same file). T006 after T005.
- US2 (T007 to T010) needs US1 complete.
- T011 to T013 after US2.

## Implementation Strategy

MVP is US1: T001 to T006 clear the 20 errors. Do not merge before US2 passes, because a type
clean-up must not change behavior in a live service.
