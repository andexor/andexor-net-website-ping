# Quickstart: Validate the Pylance fix

1. Open `src/worker.py` in VS Code. Confirm the Problems panel shows 0 entries for it (was 20).
2. Run `./run.sh`, then `curl -i -X POST localhost:<port>/api/v1/ping`. Expect 204 with no body.
3. Run `./preview-test.sh`. Expect the health check and the test ping to pass.
4. Force a failure at each step (read_config, read_headers, log_headers, make_timestamp,
   db_insert, cors_origin), for example by temporarily raising in that statement. Expect a 500
   with `{"ok": false}` and a log line `ping_error step=<step> error=<Name>: <text> line=<n>`.
5. Confirm that when there is no traceback the log line ends after the description, with no
   `line=` part.
6. Grep the file for `type: ignore` and `pyright:` comments. Expect none.
