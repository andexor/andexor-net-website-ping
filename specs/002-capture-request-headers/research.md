# Research: Capture More Request Headers

Decisions for `specs/002-capture-request-headers/spec.md`. Items marked VERIFY are checked while
implementing and then rewritten as results.

## R1. Adding columns to an existing D1 table

- **Decision**: `scripts/migrate_db.py` reads `PRAGMA table_info(ping)` through `cf d1 query`, and
  runs `ALTER TABLE ping ADD COLUMN <name> TEXT` only for columns that are missing.
- **Rationale**: SQLite and D1 have no `ADD COLUMN IF NOT EXISTS`. Checking first makes the script
  safe to repeat. `ALTER TABLE ... ADD COLUMN` without a default stores NULL for existing rows and
  does not rewrite them.
- **Alternatives**: A numbered migrations directory with `wrangler d1 migrations`. Rejected: this
  repo has one table and uses `cf`, not Wrangler, for D1 (constitution II, VI). Recreating the
  table and copying rows. Rejected: riskier and needless.
- **Verified 2026-11-14 (T004)**: `cf d1 query <id> --sql "PRAGMA table_info(ping)"` returns the usual
  array of statement results, and the column names are in each row's `name` in `results`. One
  `ALTER TABLE ping ADD COLUMN <name> TEXT` per `cf d1 query` call succeeds on the preview database.
  The first run added all six columns, a second run added none, existing rows kept their values
  with NULL in the new columns, and the four `idx_ping_*` indexes are unchanged. The Worker that was
  deployed before this feature kept returning 204 against the migrated database.

## R2. Keeping the log and the stored set identical

- **Decision**: A single `STORED_HEADERS` tuple in `src/worker.py`. The log object and the INSERT
  are both built from it.
- **Rationale**: Satisfies FR-006 without a deny-list, and adding a stored header later changes
  one line.
- **Alternatives**: Log everything except `Cookie` and `Authorization`. Rejected: a deny-list
  leaks any header it does not name.

## R3. Header names and casing

- **Decision**: Names in the tuple are lower case. Starlette's `request.headers` is
  case-insensitive for lookups and `dict(request.headers)` has lower-case keys.
- **Rationale**: It is what the Worker receives, and it matches the log keys in the spec.
- **Verified 2026-11-14 (T007)**: on the preview all six headers arrive and are stored: `cf-connecting-ip`,
  `cf-ipcountry`, `cf-ray`, `host` (the preview host name), `user-agent`, and `x-real-ip`. A POST
  with no extra headers still gets all six, because Cloudflare and curl add them. Cloudflare
  replaces any `X-Real-IP` sent by the caller with the connecting client address (a test value of
  203.0.113.9 was stored as the real address), so `x_real_ip` cannot be spoofed by the caller and
  usually equals `cf_connecting_ip`. The columns are NULL only when a request truly lacks the header.

## R4. Deployment order and the CI token

- **Decision**: Run the migration by hand, preview first, then production before the merge.
- **Rationale**: The CI token has no D1 permission (CICD.md), and giving it one would widen its
  reach for a one-time change. The change only adds nullable columns, so the old Worker version
  keeps working during the gap.

## R5. Testing approach

- **Decision**: No test framework. Verification is the preview smoke test and the quickstart.
- **Rationale**: Constitution VI and the spec assumptions.
