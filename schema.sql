-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Andexor Network, Inc.
-- Author: Ed Jenkins <ed@andexor.net>

-- One row per link click. Applied by preview-create.sh and scripts/create_db.py.
-- Keep each statement on its own lines and do not put "--" inside a statement:
-- the scripts drop lines that start with "--" and send the rest as one query.

CREATE TABLE IF NOT EXISTS ping (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT NOT NULL,
    referer     TEXT,
    ping_from   TEXT,
    ping_to     TEXT,
    cf_connecting_ip TEXT,
    cf_ipcountry     TEXT,
    cf_ray           TEXT,
    host             TEXT,
    user_agent       TEXT,
    x_real_ip        TEXT
);

CREATE INDEX IF NOT EXISTS idx_ping_received_at ON ping (received_at);
CREATE INDEX IF NOT EXISTS idx_ping_referer ON ping (referer);
CREATE INDEX IF NOT EXISTS idx_ping_ping_from ON ping (ping_from);
CREATE INDEX IF NOT EXISTS idx_ping_ping_to ON ping (ping_to);
