# Contract changes: Capture More Request Headers

Only what differs from `specs/001-click-ping-logging/contracts/http-api.md`. Paths, methods,
status codes, CORS, health, and the error answer are unchanged.

## POST /api/v1/ping

- **Stored**: the row now also holds `cf_connecting_ip` (from `CF-Connecting-IP`), `cf_ipcountry`
  (`CF-IPCountry`), `cf_ray` (`CF-Ray`), `host` (`Host`), `user_agent` (`User-Agent`), and
  `x_real_ip` (`X-Real-IP`). An absent header is stored as NULL.
- **Logged**: one JSON line, with no added escape characters, holding only the stored request
  headers that are present, under their lower-case names, for example
  `{"referer": "https://andexor.net/a", "ping-from": "...", "ping-to": "...", "host": "andexor.net", "user-agent": "..."}`.
  Every other request header, including `Cookie` and `Authorization`, is not logged.
- **Response**: unchanged. 204 with no body on success. 500 with `{"ok": false}` on failure.

## Error logging

The step names are unchanged: `read_config`, `cors_origin`, `read_headers`, `log_headers`,
`make_timestamp`, `db_insert`. Selecting the stored headers for the log is part of `log_headers`,
and building the INSERT from the stored header set is part of `db_insert`.

## scripts/migrate_db.py

`uv run scripts/migrate_db.py [--preview]` adds any of the six columns that are missing from the
`ping` table of the production database, or of the preview database with `--preview`. It prints the
columns it added (or that none were needed), never drops or changes data, and is safe to run more
than once.
