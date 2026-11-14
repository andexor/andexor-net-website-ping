# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Andexor Network, Inc.
# Author: Ed Jenkins <ed@andexor.net>

"""Create the production D1 database and its table, and record its id in wrangler.jsonc.

Idempotent. Uses the cf CLI (already logged in), so no API token is stored in the repo.
wrangler.jsonc must be plain JSON, with no comments.

Usage: uv run scripts/create_db.py
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WRANGLER_FILE = ROOT / "wrangler.jsonc"
SCHEMA_FILE = ROOT / "schema.sql"


def cf(*args: str) -> object:
    result = subprocess.run(["cf", *args], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"error: cf {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def main() -> None:
    config = json.loads(WRANGLER_FILE.read_text())
    binding = config["d1_databases"][0]
    name = binding["database_name"]

    preview_names = [d["database_name"] for d in config.get("previews", {}).get("d1_databases", [])]
    if name in preview_names:
        sys.exit(f"error: {name} is also the preview database")

    found = [d for d in cf("d1", "list", "--name", name) or [] if d["name"] == name]
    if found:
        db_id = found[0]["uuid"]
        print(f"D1 database {name} already exists")
    else:
        print(f"Creating D1 database {name}")
        db_id = cf("d1", "create", "--name", name)["uuid"]

    # Statements use IF NOT EXISTS, so this is repeatable. Comment lines are dropped.
    sql = " ".join(
        line for line in SCHEMA_FILE.read_text().splitlines() if not line.lstrip().startswith("--")
    )
    cf("d1", "query", db_id, "--sql", sql)
    print(f"Applied {SCHEMA_FILE.name} to {name}")

    if binding.get("database_id") != db_id:
        binding["database_id"] = db_id
        WRANGLER_FILE.write_text(json.dumps(config, indent=4) + "\n")
        print(f"Wrote database_id to {WRANGLER_FILE.name}. Commit it.")
    else:
        print(f"{WRANGLER_FILE.name} already has the database_id")


if __name__ == "__main__":
    main()
