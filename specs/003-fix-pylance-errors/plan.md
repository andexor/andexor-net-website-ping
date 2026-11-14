# Implementation Plan: Fix Pylance Type Errors

**Branch**: `7-fix-pylance-errors` | **Date**: 2026-11-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-fix-pylance-errors/spec.md`

## Summary

Make `src/worker.py` report 0 Pylance problems (down from 20) with no behavior change. Two edits:
type the `call_next` parameter and the middleware return values, and replace each unguarded
`e.__traceback__.tb_lineno` with an inline conditional that leaves out ` line=<n>` when there is no
traceback. See [research.md](research.md).

## Technical Context

**Language/Version**: Python >=3.14 (Pyodide on Cloudflare Workers)

**Primary Dependencies**: FastAPI (Starlette), `workers`, `pyodide.ffi`. No new dependencies.

**Storage**: N/A (no data change)

**Testing**: No test runner (constitution VI). Checked with Pylance diagnostics, the preview smoke test, and forced failures of each error step.

**Target Platform**: Cloudflare Workers (Python)

**Project Type**: web-service

**Performance Goals**: N/A, no change

**Constraints**: Principle IV (inline try/except per statement, no helper); no disabled rules or blanket suppressions (FR-006)

**Scale/Scope**: one file, 20 diagnostics, 6 except blocks, 2 middleware functions

## Constitution Check

| Principle | Result |
|-----------|--------|
| I. Specs are truth | Pass. Spec 003 written first; the log-line change is recorded in it. |
| II. Standard tooling | Pass. No tooling change. |
| III. Tested before production | Pass. Normal PR pipeline. |
| IV. Errors and health | Pass. Each except block keeps its own inline logging; the traceback guard is written inline in each block, not in a helper. |
| V. Repeatable scripts | N/A. |
| VI. Simplicity | Pass. No tests, validation, or machinery added. |

Re-checked after design: no change.

## Project Structure

### Documentation (this feature)

```text
specs/003-fix-pylance-errors/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── tasks.md             # created by /speckit-tasks
```

No `contracts/`: the external interface does not change.

### Source Code

```text
src/worker.py            # the only file changed
```

**Structure Decision**: single file edit; nothing is added or moved.
