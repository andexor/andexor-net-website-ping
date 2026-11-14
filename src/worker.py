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

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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


Default = asgi.entrypoint(app)
