# HTTP Contract: Click Ping Logging

Base: `https://andexor.net` (production), `https://preview-andexor-net-website-ping.andexor.workers.dev`
(preview). All paths are under `/api/v1/ping`.

## POST /api/v1/ping

Records one click.

**Request headers used**: `Referer`, `Ping-From`, `Ping-To` (all optional). Every other header is
logged and ignored. A request body is ignored.

| Result | Status | Body |
|---|---|---|
| Recorded | 204 | none |
| Any failure | 500 | `{"ok": false}` |

**Side effects**: one row in `ping` (see [data-model.md](../data-model.md)). One log line holding all
request headers as a single JSON object.

## OPTIONS /api/v1/ping

CORS preflight. Status 204, no body, with the CORS headers below.

## GET /api/v1/ping/health

| Result | Status | Body |
|---|---|---|
| Alive | 200 | `{"ok": true}` |
| Any failure | 500 | `{"ok": false}` |

Liveness only. It never queries D1.

## CORS headers (all responses)

| Header | Value |
|---|---|
| `Access-Control-Allow-Origin` | The request `Origin` if it is in `ALLOWED_ORIGINS`, otherwise the first entry |
| `Access-Control-Allow-Methods` | `POST, OPTIONS` |
| `Access-Control-Allow-Headers` | `Content-Type` |
| `Vary` | `Origin` |

`ALLOWED_ORIGINS` is a comma-separated Worker var. Value in both environments:
`https://andexor.net,http://localhost:8787`.

## Error logging

Every try/except in the Worker writes its own log line with the step name, the error name, the
error description, and the source line, for example
`ping_error step=db_insert error=D1_ERROR: no such table: ping line=57`. The step names are unique,
so a log line identifies exactly which block failed.
Nothing about the error appears in the response.

| Step | Code it guards |
|---|---|
| `read_config` | Reading `ALLOWED_ORIGINS` from the Worker environment (middleware) |
| `cors_origin` | Matching the `Origin` header and setting the CORS response headers (middleware) |
| `read_headers` | Copying the request headers in `POST /api/v1/ping` |
| `log_headers` | Writing every request header to the log as one JSON line |
| `make_timestamp` | Building `received_at` |
| `db_insert` | Reading the three headers and inserting the row into D1 |
