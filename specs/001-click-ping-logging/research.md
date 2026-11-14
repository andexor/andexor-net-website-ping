# Research: Click Ping Logging

Sources: Cloudflare documentation (Python Workers, FastAPI, D1 from Python Workers) searched
2026-11-14, and the existing repo files. Items marked VERIFY could not be settled from
documentation and are checked during implementation (see [quickstart.md](./quickstart.md)).

## R1. Python version

- **Decision**: Python 3.14, as decided by the project owner. Keep `requires-python = ">=3.14"`.
- **Rationale**: Already committed, and the owner chose it. The Cloudflare FastAPI page shows
  `>=3.13`.
- **Confirmed (owner)**: Python 3.14 works. `andexor-net-website-contact-us` runs on it.

## R2. Worker entrypoint

- **Decision**: Use the `workers` module's ASGI support. Prefer `Default = asgi.entrypoint(app)`.
  Fall back to a `WorkerEntrypoint` subclass with `await asgi.fetch(app, request, self.env)`.
- **Rationale**: Both forms are in the current Cloudflare docs. The class form gives control over
  `env` if the short form does not expose it.
- **Alternatives**: Raw `WorkerEntrypoint.fetch` without FastAPI. Rejected, because FastAPI is
  already a dependency and gives routing and method handling for free.
- **VERIFY**: that the D1 binding is reachable from route handlers as `request.scope["env"].DB`
  with the short form.

## R3. Writing to D1 from Python

- **Decision**: `await env.DB.prepare("INSERT INTO ping (received_at, referer, ping_from, ping_to) VALUES (?, ?, ?, ?)").bind(...).run()`.
  Use bound parameters only.
- **Rationale**: This is the documented Python pattern. Bound parameters keep header values from
  being interpreted as SQL, which matters because callers are unauthenticated.
- **Decision (owner)**: a missing header, or a header whose value is `None`, is stored as NULL in
  the database. D1 rejects JavaScript `undefined`, so the Worker MUST pass an explicit JS `null`
  for these fields and must not rely on how a Python `None` converts.
- **VERIFY**: the exact conversion call (for example `js.null`) works in the Python Workers runtime.

## R4. CORS

- **Decision**: Write a small middleware instead of FastAPI's `CORSMiddleware`.
- **Rationale**: The spec requires echoing `Origin` when listed and otherwise answering with the
  first listed origin. `CORSMiddleware` omits the header for unlisted origins instead.
- **Alternatives**: `CORSMiddleware` with the list. Rejected for that reason.

## R5. Error handling

- **Decision (owner)**: No catch-all handler. Put a `try/except` block around each piece of code
  that could raise an error: reading and logging the headers, building the timestamp, the D1 write,
  and the CORS handling. Each block is written inline at the spot it guards, with its own log
  line, and returns HTTP 500 with `{"ok": false}`. Normal 404 and 405 answers from routing are left
  alone.
- **Log line content**: a fixed step name unique to that block (for example `db_insert`), the error
  name, the error description, and the line number of the failing statement in `src/worker.py`.
  Python has no `__LINE__`, so take the line from the exception, `e.__traceback__.tb_lineno`,
  which is the line in our code where the error passed through. Do not use `inspect` or
  `sys._getframe` inside a shared function, because that reports the helper's line.
- **Rationale (owner)**: Observability, production support, and maintenance. A failure on line 10
  and a different failure on line 20 must be distinguishable in the logs. A shared handler or
  helper would report its own location for every error, so it is not used, even though inline
  blocks repeat a few lines. Do not trade log detail for less code.
- **Alternatives**: A single middleware, `@app.exception_handler(Exception)`, or a logging helper
  called from each `except`. All rejected by the owner for hiding where the failure happened.

## R6. Header logging

- **Decision**: Log `json.dumps(dict(request.headers), ensure_ascii=False)` as one line.
- **Rationale**: `ensure_ascii=False` avoids added escape sequences for non-ASCII values, as the
  spec requires. Repeated header names collapse to one entry, which is acceptable here.
- **Owner decision**: log every header, including `Cookie` and `Authorization`, for the limited
  initial testing. Do not filter anything yet. The log will be reviewed by hand and then trimmed,
  and useful headers may be added to the table. Until then the logs are sensitive.
- **Log retention**: Workers Logs and traces retention is fixed by plan (3 days Free, 7 days Paid,
  7 days is the maximum) and has no `wrangler.jsonc` setting. The account is on Workers Paid, so
  it is already 7 days and there is nothing to configure.

## R7. Timestamp

- **Decision**: `datetime.now(timezone.utc)` formatted as ISO 8601 with a `Z` suffix and
  millisecond precision, set in the Worker.
- **Rationale**: Matches FR-002. Millisecond text sorts correctly as a string.

## R8. Preview and deploy mechanics

- **Decision**: Use the existing scripts and config. CI runs `uv run pywrangler preview --name preview`
  then `uv run pywrangler deploy`. The preview Worker is created once in advance (a manual task),
  not by the pipeline.
- **Rationale**: Already built and documented in `CICD.md`. The user asked that the pipeline not
  create the preview Worker.
- **VERIFY**: that `pywrangler preview` works against an existing Worker with the `previews` block.

## R9. Testing approach

- **Decision**: No test framework. The preview smoke test (health check, then POST expecting 204)
  and the quickstart are the verification.
- **Rationale**: Constitution VI and the spec assumptions exclude unit and functional tests.
