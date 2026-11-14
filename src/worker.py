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
        logger.info(json.dumps(headers, ensure_ascii=False))
    except Exception as e:
        logger.error(f"ping_error step=log_headers error={type(e).__name__}: {e} line={e.__traceback__.tb_lineno}")
        return JSONResponse({"ok": False}, status_code=500)

    try:
        received_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except Exception as e:
        logger.error(f"ping_error step=make_timestamp error={type(e).__name__}: {e} line={e.__traceback__.tb_lineno}")
        return JSONResponse({"ok": False}, status_code=500)

    try:
        referer = headers.get("referer")
        ping_from = headers.get("ping-from")
        ping_to = headers.get("ping-to")
        await request.scope["env"].DB.prepare(
            "INSERT INTO ping (received_at, referer, ping_from, ping_to) VALUES (?, ?, ?, ?)"
        ).bind(
            received_at,
            jsnull if referer is None else referer,
            jsnull if ping_from is None else ping_from,
            jsnull if ping_to is None else ping_to,
        ).run()
    except Exception as e:
        logger.error(f"ping_error step=db_insert error={type(e).__name__}: {e} line={e.__traceback__.tb_lineno}")
        return JSONResponse({"ok": False}, status_code=500)

    return Response(status_code=204)


Default = asgi.entrypoint(app)
