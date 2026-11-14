# Quickstart: Click Ping Logging

Validation scenarios for the feature. Setup steps that need a person are in
[MANUAL-TASKS.md](../../MANUAL-TASKS.md). Endpoint details are in [contracts/http-api.md](./contracts/http-api.md).

## Prerequisites

- `cf` logged in, `uv` installed, `uv sync` done.
- Production and preview databases and the preview Worker created (MANUAL-TASKS.md Step 1).

## Scenarios

Run against the preview first (`NAME=preview`, URL `https://preview-andexor-net-website-ping.andexor.workers.dev`).

1. **Deploy the preview**: `uv run pywrangler preview --name preview`.
2. **Health (US3)**: `curl -si $URL/api/v1/ping/health`. Expect 200 and `{"ok": true}`.
3. **Record a click (US1)**:
   `curl -si -X POST $URL/api/v1/ping -H 'Referer: https://andexor.net/a' -H 'Ping-From: https://andexor.net/a' -H 'Ping-To: https://example.com/'`.
   Expect 204 and no body. Then `uv run scripts/query_db.py --preview` shows one new row with all
   four fields filled. Then send a second POST with no `Ping-*` headers: expect 204 and a row
   whose missing fields are NULL (research R3).
4. **Header log (US1)**: in the Worker logs, find one JSON line with the stored request headers only (see `specs/002-capture-request-headers/`).
5. **CORS (US2)**:
   `curl -si -X OPTIONS $URL/api/v1/ping -H 'Origin: https://andexor.net'` returns 204 with the
   origin echoed. Repeat with `-H 'Origin: https://evil.example'` and expect `https://andexor.net`.
6. **Failure handling (US4)**: temporarily rename the table in the insert, redeploy the preview,
   and POST. Expect 500 and `{"ok": false}`, and an error log line that names the step (`db_insert`) and the source line. Revert.
7. **Isolation (US5)**: `uv run scripts/query_db.py` (production) shows none of the test rows.
8. **Pipeline gate (US5)**: follow the negative test in `CICD.md` section 4.

## Production check after the first merge

`curl -si https://andexor.net/api/v1/ping/health` returns 200 and `{"ok": true}`. Do not POST test
pings to production.
