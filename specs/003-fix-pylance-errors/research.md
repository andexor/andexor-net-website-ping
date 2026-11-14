# Research: Fix Pylance Type Errors

## R1. Typing `call_next`

- **Decision**: Annotate it as `Callable[[Request], Awaitable[Response]]` (from `collections.abc`)
  and annotate both middleware functions as returning `Response`.
- **Rationale**: This is the signature Starlette's `@app.middleware("http")` passes. It removes the
  four missing-annotation errors, makes `response` known, and makes `response.headers` known, which
  clears the unknown-type errors that follow from them. `JSONResponse` is a `Response`, so both
  return paths fit.
- **Alternatives**: `BaseHTTPMiddleware`'s own `RequestResponseEndpoint` alias. Rejected: it is
  not a stable public import. `Any`. Rejected: hides the type, against the intent of FR-002.

## R2. The optional traceback

- **Decision**: In each except block, build the suffix inline:
  `line = f" line={e.__traceback__.tb_lineno}" if e.__traceback__ else ""`, and log
  `...: {e}{line}`.
- **Rationale**: The conditional narrows `e.__traceback__` so the checker is satisfied. It stays in
  each block, so the log still reports the failing statement and Principle IV holds. It omits the
  part entirely when there is no traceback, as the spec requires (no `line=0`).
- **Alternatives**: A helper that formats the line. Rejected: Principle IV forbids shared helpers
  for this logging. `# type: ignore` or an `assert`. Rejected: suppression (FR-006) or a behavior
  change on failure.

## R3. Verification

- **Decision**: Confirm 0 problems with the editor's diagnostics, then run `./preview-test.sh`.
  Force each of the six error steps once on the preview to compare log lines.
- **Rationale**: There is no test runner and Principle VI forbids adding one for this.
- **Alternatives**: Add pyright to the project. Rejected: a new dependency (FR-007).

## R4. Origin that may be None (found while implementing)

- **Decision**: In `cors`, test `origin is not None and origin in allowed_origins`.
- **Rationale**: `request.headers.get("origin")` is `str | None`, and the checker reported the `None` branch as an error once the middleware was typed (a 21st problem hidden by the unknown types). A missing origin was never in the allowed list, so behavior is identical.
