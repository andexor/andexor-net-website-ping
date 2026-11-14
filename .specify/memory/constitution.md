# Andexor Ping Service Constitution

## Core Principles

### I. Specifications Are the Source of Truth
The feature specifications under `specs/` define what the service does. Code, scripts, and
documents MUST match them. When behavior changes, the specification MUST be updated first or in
the same change, and `README.md`, `setup.md`, and `CICD.md` MUST be kept consistent with it.
`PRD.md` only seeded the constitution and the initial specifications. It is not a living
document and MUST NOT be treated as authoritative.
Rationale: one authoritative description prevents the documents and the code from drifting apart.

### II. Standard Tooling
Python packages MUST be managed with `uv`. Local runs and deploys MUST use `pywrangler` through
`uv run`. Cloudflare resources outside the Worker (D1, zones, previews) MUST be managed with the
`cf` CLI. API tokens MUST NOT be stored in the repo.
Rationale: one toolchain keeps setup reproducible and keeps credentials out of source control.

### III. Nothing Reaches Production Untested
Production MUST deploy only after a preview deploy and its smoke test (health check plus a real
POST) pass. Preview and production MUST use separate databases, and no script or configuration may
let a preview touch production data. The smoke-test POST MUST never run against production.
Rationale: a bad change must never reach production, and test data must never mix with real data.

### IV. Errors and Health
Every piece of code that can raise an error MUST be surrounded by its own try/except block, written
inline at that spot. Each block MUST log the failing step, the error name and description, and the
source line of the failing statement, then return HTTP 500 with `{"ok": false}`. A catch-all
handler, shared middleware, or helper function MUST NOT do the logging for these blocks, because
it would report its own location and hide where the failure happened. Error detail MUST stay in the logs and
MUST NOT appear in responses. `GET /api/v1/ping/health` MUST check liveness only and MUST NOT
test the database or any other dependency.
Rationale: callers learn only that a request failed, operators get the detail from the logs, and
a dependency problem cannot cascade into a failing health check. Specific, located log lines are
what production support needs, so development convenience MUST NOT reduce that detail.

### V. Repeatable Scripts
Every setup script MUST be idempotent. Names (Worker, databases, bindings) MUST be read from the
configuration, not hard-coded. Every preview or other non-production environment that a script
creates MUST have a committed script that tears it down. Production resources MUST NOT have a
teardown script, and the preview teardown MUST refuse to touch production. Setup that cannot be
scripted MUST be listed in the manual task list in `MANUAL-TASKS.md`.
Rationale: scripted create and delete make preview setup and decommissioning safe to repeat, and
the absence of a production teardown script means production data cannot be deleted by accident.

### VI. Simplicity
The service MUST NOT add validation, authentication, rate limiting, bot checks, notifications,
or unit tests unless a specification changes to require them. New features and columns start in a
specification.
Rationale: the service counts clicks. Extra machinery adds risk and cost to a path that runs on
every link click.

## File Conventions

- Every source, script, and configuration file that allows comments MUST begin with the SPDX
  header (Apache-2.0, Andexor Network, Inc., Author Ed Jenkins), copied from an existing file.
- Only straight quotes (') and (") MAY be used, in every file. Typographic quotes and their
  escapes MUST NOT appear.
- `wrangler.jsonc` MUST stay plain JSON with no comments, because scripts edit it.

## Delivery Workflow

- Work follows Spec Kit: constitution, specification, plan, tasks, implement.
- Changes reach `main` only through a pull request that passes the required check
  `Preview and smoke test`.
- Workers Builds MUST stay disconnected so that only GitHub Actions deploys.

## Governance

This constitution supersedes other practices in this repo. Amendments MUST be made through a pull
request that states the reason and updates the version. Versioning follows semantic versioning:
MAJOR for removing or redefining a principle, MINOR for adding a principle or materially
expanding guidance, PATCH for wording fixes. Reviewers MUST check each pull request against these
principles, and any deviation MUST be justified in the pull request.

**Version**: 1.1.0 | **Ratified**: 2026-11-14 | **Last Amended**: 2026-11-14
