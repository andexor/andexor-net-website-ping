# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Andexor Network, Inc.
# Author: Ed Jenkins <ed@andexor.net>

"""Add the columns that are missing from the ping table of an existing database.

SQLite has no ADD COLUMN IF NOT EXISTS, so this reads the table's columns first and adds only the
ones that are missing. It never drops or changes data and is safe to run more than once. A new
database made from schema.sql already has every column, so there is nothing to add.

Reads the production database by default. Pass --preview for the preview database.

Usage: uv run scripts/migrate_db.py [--preview]
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Columns added after the first version of the table. All nullable TEXT, and not indexed.
NEW_COLUMNS = ["cf_connecting_ip", "cf_ipcountry", "cf_ray", "host", "user_agent", "x_real_ip"]


def query(database_id: str, sql: str) -> list[dict]:
    result = subprocess.run(
        ["cf", "d1", "query", database_id, "--sql", sql],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"error: cf d1 query failed for {sql!r}: {result.stderr.strip()}")
    try:
        statements = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        sys.exit(f"error: cf d1 query did not return JSON: {e}")
    return [row for statement in statements for row in statement["results"]]


def main() -> None:
    config = json.loads((ROOT / "wrangler.jsonc").read_text())
    if "--preview" in sys.argv[1:]:
        binding = config["previews"]["d1_databases"][0]
    else:
        binding = config["d1_databases"][0]
    database_id = binding["database_id"]

    existing = {row["name"] for row in query(database_id, "PRAGMA table_info(ping)")}
    if not existing:
        sys.exit(f"error: table ping not found in {binding['database_name']}. Run create_db.py or preview-create.sh first.")

    added = []
    for column in NEW_COLUMNS:
        if column not in existing:
            query(database_id, f"ALTER TABLE ping ADD COLUMN {column} TEXT")
            added.append(column)

    if added:
        print(f"{binding['database_name']}: added {', '.join(added)}")
    else:
        print(f"{binding['database_name']}: nothing to add")


if __name__ == "__main__":
    main()
