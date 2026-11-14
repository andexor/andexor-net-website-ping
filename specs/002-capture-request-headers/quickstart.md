# Quickstart: Capture More Request Headers

Run against the preview (`URL=https://preview-andexor-net-website-ping.andexor.workers.dev`).

## Prerequisites

`MANUAL-TASKS.md` is done. `uv sync` has run.

## Scenarios

1. **Migrate the preview (US3)**: `uv run scripts/migrate_db.py --preview`. Expect the six column
   names to be reported as added. Run it again and expect that nothing is added. Confirm
   `uv run scripts/query_db.py --preview` still prints the old rows, with the six new fields null.
2. **Indexes unchanged (US3)**:
   `cf d1 query <preview id> --sql "SELECT name FROM sqlite_master WHERE type='index'"` lists the
   same four `idx_ping_*` indexes as before.
3. **Store the new headers (US1)**: deploy with `uv run pywrangler preview --name preview`, then
   `curl -si -X POST $URL/api/v1/ping -H 'Referer: https://andexor.net/a' -H 'Ping-From: https://andexor.net/a' -H 'Ping-To: https://example.com/' -H 'X-Real-IP: 203.0.113.9' -H 'User-Agent: quickstart'`.
   Expect 204. `uv run scripts/query_db.py --preview` shows a row with `host`, `user_agent`
   (`quickstart`), `x_real_ip` (`203.0.113.9`), and the Cloudflare fields filled where Cloudflare
   sent them.
4. **Missing headers (US1)**: POST with no extra headers. Expect 204 and NULL in `x_real_ip`.
5. **Log holds only stored headers (US2)**: POST once with `-H 'Cookie: secret=1' -H 'Authorization: Bearer x' -H 'X-Made-Up: 1'`.
   In the Worker logs the line for that ping holds the stored headers and none of the three others.
6. **Failure handling still works (base scenario 6)**: unchanged and not repeated here.
7. **Fresh database (US3)**: create a throwaway database with `cf d1 create`, apply `schema.sql` to
   it, and confirm `PRAGMA table_info(ping)` lists all eleven columns and the same four `idx_ping_*`
   indexes. Delete the throwaway database. (A preview delete and recreate would change the preview
   database id in `wrangler.jsonc`, so it is not used here.)
8. **Production (US3)**: `uv run scripts/migrate_db.py` before the merge. After the merge,
   `curl -si https://andexor.net/api/v1/ping/health` returns 200. Do not POST test pings to
   production.
