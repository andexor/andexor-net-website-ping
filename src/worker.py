# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Andexor Network, Inc.
# Author: Ed Jenkins <ed@andexor.net>

"""Andexor Ping Service: logs link clicks from andexor.net to D1.

Error handling rule (constitution, Principle IV): every statement that can raise an error is
inside its own inline try/except. Each except logs one line,
    ping_error step=<step> error=<ErrorName>: <description> line=<n>
and returns 500 with {"ok": false}. There is deliberately no shared helper or catch-all handler,
so the logged step and line always point at the statement that failed.

Step names: read_config, read_headers, log_headers, make_timestamp, db_insert, cors_origin.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pyodide.ffi import jsnull
from workers import asgi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ping")

# The request headers that are stored, as (header name, column name). Storing and logging are both
# derived from this tuple, so a header cannot be logged without being stored and every other header
# is left out of the log without being named.
STORED_HEADERS = (
    ("referer", "referer"),
    ("ping-from", "ping_from"),
    ("ping-to", "ping_to"),
    ("cf-connecting-ip", "cf_connecting_ip"),
    ("cf-ipcountry", "cf_ipcountry"),
    ("cf-ray", "cf_ray"),
    ("host", "host"),
    ("user-agent", "user_agent"),
    ("x-real-ip", "x_real_ip"),
)

app = FastAPI()


@app.middleware("http")
async def load_config(request: Request, call_next):
    try:
        request.state.allowed_origins = [
            origin.strip()
            for origin in request.scope["env"].ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]
    except Exception as e:
        logger.error(f"ping_error step=read_config error={type(e).__name__}: {e} line={e.__traceback__.tb_lineno}")
        return JSONResponse({"ok": False}, status_code=500)
    return await call_next(request)


@app.middleware("http")
async def cors(request: Request, call_next):
    response = await call_next(request)
    allowed_origins = getattr(request.state, "allowed_origins", None)
    if not allowed_origins:
        return response
    try:
        origin = request.headers.get("origin")
        response.headers["Access-Control-Allow-Origin"] = origin if origin in allowed_origins else allowed_origins[0]
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Vary"] = "Origin"
    except Exception as e:
        logger.error(f"ping_error step=cors_origin error={type(e).__name__}: {e} line={e.__traceback__.tb_lineno}")
        return JSONResponse({"ok": False}, status_code=500)
    return response


@app.options("/api/v1/ping")
async def ping_preflight():
    return Response(status_code=204)


@app.get("/api/v1/ping/health")
async def health():
    return {"ok": True}


@app.post("/api/v1/ping")
async def ping(request: Request):
    try:
        headers = dict(request.headers)
    except Exception as e:
        logger.error(f"ping_error step=read_headers error={type(e).__name__}: {e} line={e.__traceback__.tb_lineno}")
        return JSONResponse({"ok": False}, status_code=500)

    try:
        logger.info(json.dumps({name: headers[name] for name, _ in STORED_HEADERS if name in headers}, ensure_ascii=False))
    except Exception as e:
        logger.error(f"ping_error step=log_headers error={type(e).__name__}: {e} line={e.__traceback__.tb_lineno}")
        return JSONResponse({"ok": False}, status_code=500)

    try:
        received_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except Exception as e:
        logger.error(f"ping_error step=make_timestamp error={type(e).__name__}: {e} line={e.__traceback__.tb_lineno}")
        return JSONResponse({"ok": False}, status_code=500)

    try:
        columns = ", ".join(column for _, column in STORED_HEADERS)
        marks = ", ".join("?" for _ in STORED_HEADERS)
        values = [jsnull if headers.get(name) is None else headers[name] for name, _ in STORED_HEADERS]
        await request.scope["env"].DB.prepare(
            f"INSERT INTO ping (received_at, {columns}) VALUES (?, {marks})"
        ).bind(received_at, *values).run()
    except Exception as e:
        logger.error(f"ping_error step=db_insert error={type(e).__name__}: {e} line={e.__traceback__.tb_lineno}")
        return JSONResponse({"ok": False}, status_code=500)

    return Response(status_code=204)


Default = asgi.entrypoint(app)
