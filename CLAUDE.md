# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

Pre-implementation. The repo holds the PRD, tooling scripts, `schema.sql`, `scripts/`, and Cloudflare config. The Worker source (`src/worker.py`, referenced by `wrangler.jsonc`) and the CI workflow do not exist yet. The specs under `specs/` (Spec Kit) are the source of truth for behavior. `PRD.md` and `prompt.md` only seeded the constitution and initial specs and are not kept up to date. When changing behavior, update the spec first and keep `README.md`, `setup.md`, and `CICD.md` consistent with it. Manual setup steps live in `MANUAL-TASKS.md`.

## What this is

A Python FastAPI Cloudflare Worker that logs link clicks from andexor.net to a D1 database. Browsers call it through the `ping` attribute of `<a>` elements, so the endpoint must accept the browser's `Ping-From`, `Ping-To`, and `Referer` headers.

- `POST /api/v1/ping` logs all request headers as JSON and stores a subset in D1, then returns 204 with no body.
- `OPTIONS /api/v1/ping` is the CORS preflight (204). `GET /api/v1/ping/health` returns `{"ok": true}`.
- CORS origin comes from the `ALLOWED_ORIGINS` var in `wrangler.jsonc`. It echoes `Origin` if listed, otherwise the first entry.
- D1 is reached through the `DB` binding on `request.scope["env"]`. FastAPI is wired in with `asgi.fetch(app, request.js_object, self.env)`.
- Table `ping` (DDL in `schema.sql`, `CREATE TABLE IF NOT EXISTS`). `received_at` is set by the Worker in UTC. All columns are indexed, duplicates allowed.

## Commands

Python tooling runs through `uv` and `pywrangler` (package `workers-py`), which wraps Wrangler and reads `wrangler.jsonc`. Python >=3.14. `uv` uses `exclude-newer = "1 week"`, so only dependencies at least a week old resolve.

- `./run.sh`: local dev (`uv run pywrangler preview`).
- `./deploy.sh`: `pywrangler deploy` to production, then runs `scripts/query_db.py` to warm the DB connection.
- `./preview-test.sh`: deploys the shared `preview` Worker, then health-checks it and POSTs a test ping.
- `./health.sh`: health-checks preview and production.
- `./preview-create.sh` / `./preview-delete.sh`: one-time creation and teardown of the preview D1 database (`andexor-net-website-ping-prev`), schema, and the `previews` block in `wrangler.jsonc`. They use `cf` and `jq`, and need `wrangler.jsonc` to stay plain JSON with no comments.
- `./plantuml.sh`: renders `doc/uml/*.puml` to `dist/uml` using the jar in `.tools/`.
- `install-uv.sh`, `install-spec-kit.sh`, `install-plantuml.sh`: pre-requisite installers (see `setup.md`).

There is no test runner or linter configured yet. Prettier config is in `.prettierrc.json`.

## Infrastructure and CI/CD

- Worker `andexor-net-website-ping`, route `andexor.net/api/v1/ping*` on zone `andexor.net`. `workers_dev` is false. Preview URLs are on, and the preview Worker lives at `https://preview-andexor-net-website-ping.andexor.workers.dev`.
- Production and preview use separate D1 databases (`-prod` and `-prev`). Previews must never touch production data.
- Use the `cf` CLI for Cloudflare operations. `wrangler` is used here only indirectly through `pywrangler`.
- `CICD.md` was adapted from the sibling contact-us repo and describes the intended pipeline: PRs and merges deploy to the one shared `preview` Worker and smoke test it (health check plus a real POST, never retried, never against production). Production deploys only after the preview passes, followed by a GET-only health check.
- `.github/workflows/ci.yml` and `.github/dependabot.yml` do not exist yet.

## Spec Kit

`.specify/` holds Spec Kit config, templates, and scripts, driven through the `speckit-*` skills. `.specify/memory/constitution.md` holds the project constitution (v1.0.0).

## Conventions

- Source files carry an SPDX header (Apache-2.0, Andexor Network, Inc., Author Ed Jenkins). Copy it from an existing script.
- Branch naming follows the issue, for example `1-write-prd`.
- Every issue is assigned to `ejenkins`. Always create PRs with `--assignee ejenkins` and a review request to `andexor/write`. `ejenkins` is the only person on the project for now, so every PR is assigned to them. The `andexor/write` team is the code owner, see `.github/CODEOWNERS`.
