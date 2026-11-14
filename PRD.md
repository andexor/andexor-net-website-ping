<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 Andexor Network, Inc.
Author: Ed Jenkins <ed@andexor.net>
-->

# PRD: Andexor Ping Service

Status: DRAFT
Date: 2026-11-12

## 1. Goal

Log clicks on the website at https://andexor.net/ to a Cloudflare D1 database for monitoring and analysis.

### Description

As an SRE,
I want to count pings from links
So that I can distinguish between interactive and non-interactive use.

### Acceptance Criteria

A service will be created that will be called by browsers whenever an interactive user clicks a link.
This could happen with some automated tests, but mostly it will indicate that a human is using the site.

## 2. Context

- Name: andexor-net-website-ping
- Description: Andexor Ping Service
- The site is a Next.js app served by the Worker `andexor-net-website`
  on the custom domain `andexor.net`
  (zone id `2826c1aa23954fa65dd22d0aefca885a`,
  account id `89df54b7a586cd4489e7a8bc6cd5145d`).
- The site will call this service whenever someone
  clicks on a link on the site.
- The browser will call this service automatically
  by listing its endpoint in the `ping` attribute of `<a>` elements. Reference
  [HTML anchor element](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/a#ping)
- This service will need a Cloudflare route for
  `andexor.net/api/v1/ping*`.
- Python Workers support FastAPI. They are built, run locally, and deployed with `pywrangler` (package `workers-py`, run through `uv`),
  which wraps Wrangler and reads `wrangler.jsonc`.
  Dependencies are bundled from `pyproject.toml` on deploy.

## 3. Data model

Preview database:    D1 `andexor-net-website-ping-prev`. Table: `ping`.
Production database: D1 `andexor-net-website-ping-prod`. Table: `ping`.

This is the initial set of columns. More may be added as a result after testing begins.

| Column        | Type    | Source                                       |
|---------------|---------|----------------------------------------------|
| `id`          | INTEGER | primary key, autoincrement                   |
| `received_at` | TEXT    | UTC ISO 8601, set by the Worker              |
| `referer`     | TEXT    | request header `Referer`                     |
| `ping_from`   | TEXT    | request header `Ping-From` (the link source) |
| `ping_to`     | TEXT    | request header `Ping-To`   (the link target) |

The `id` and `received_at` columns are required.
All other fields are optional.
All fields should be indexed and allow duplicates.
The DDL lives in `schema.sql` and uses `CREATE TABLE IF NOT EXISTS`.

## 4. Service

- Language: Python
- Framework: FastAPI
  `asgi` module (`asgi.fetch(app, request.js_object, self.env)`)
- Deployment: Cloudflare Workers
- Database: D1 is reached through the `DB` binding on `request.scope["env"]`
- Worker name: `andexor-net-website-ping`
- Route: `andexor.net/api/v1/ping*` on zone `andexor.net`, declared in `wrangler.jsonc`
- Endpoints:
  - `POST /api/v1/ping`: reads the request headers,
    writes the names and values of all request headers to the log
    as a JSON object with no escape characters added
    and writes a select subset of headers to the database.
    The response code is 204 and there is no response body.
  - `OPTIONS /api/v1/ping`: CORS preflight, returns HTTP 204.
  - `GET /api/v1/ping/health`: HTTP 200 with `{"ok": true}`, for smoke tests.
- CORS: `Access-Control-Allow-Origin` echoes the request's `Origin`
  when it is in the comma-separated `ALLOWED_ORIGINS` var in `wrangler.jsonc`
  (`https://andexor.net`, `http://localhost:8787`), otherwise the first entry.
  Methods POST and OPTIONS, header Content-Type, `Vary: Origin`.

- Errors: anything that could produce an error MUST have an error handler that writes the error
  name and description to the log and returns HTTP 500 with `{"ok": false}`. No other handling.
- No validation, no authentication, no rate limiting, no bot check, no notification email.

## 5. Scripts (run locally with uv, authenticated through the cf CLI)

- `scripts/create_db.py`: creates the D1 database if it does not exist, creates the table if it
  does not exist (from `schema.sql`), and writes the resulting `database_id` into the
  `d1_databases` binding in `wrangler.jsonc`. Idempotent. Uses the `cf d1` commands through
  `subprocess`, so no API token is stored in the repo.
- `scripts/query_db.py`: selects every row from `ping` ordered by `id` and prints them as
  one JSON array to stdout. For manual testing.

## 6. Repository layout

```
PRD.md                 this document
pyproject.toml         uv project: fastapi dependency, workers-py and workers-runtime-sdk dev deps,
                       [tool.uv] exclude-newer = "1 week"
wrangler.jsonc         Worker name, main, python_workers flag, route, D1 binding, ALLOWED_ORIGINS var
schema.sql             CREATE TABLE IF NOT EXISTS ping (...)
src/worker.py          FastAPI app plus the WorkerEntrypoint Default class
scripts/create_db.py   section 5
scripts/query_db.py    section 5
README.md              project overview and links to the documents below
setup.md               how to set up, run locally, deploy, and test
CICD.md                CI/CD pipeline, preview environment, and manual setup checklist
deploy.sh, run.sh      deploy to production, run locally
preview-*.sh, health.sh  preview environment scripts and health checks
```

## 7. Tooling rules

- `uv` for all Python package management. No pip, npm, or npx for Python.
- `uv run pywrangler preview` for local development and `uv run pywrangler deploy` to deploy.
  Because the project has a `wrangler.jsonc`, Wrangler (through pywrangler) owns dev and deploy.
- `cf` CLI for Cloudflare resources outside the Worker (D1 create and query, zone lookups).
- Straight quotes only in every file.

## 8. Deployment and verification

1. `uv sync`
2. `uv run scripts/create_db.py`
3. `uv run pywrangler deploy`
4. `curl -i -X POST https://andexor.net/api/v1/ping -H 'Ping-From: https://andexor.net/' -H 'Ping-To: https://example.com/'`
   returns HTTP 204 with no body.
5. `uv run scripts/query_db.py` prints one row with `received_at`, `ping_from`, and `ping_to` populated.

## 9. Out of scope

- Changing the website to call the endpoint.
- Validation, spam protection, email or chat notifications, admin UI, data retention.
- Unit tests and functional tests.
- Docker packaging. The Worker runs on Cloudflare.
