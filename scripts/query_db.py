# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Andexor Network, Inc.
# Author: Ed Jenkins <ed@andexor.net>

"""Print every row of the ping table, ordered by id, as one JSON array.

Reads the production database by default. Pass --preview for the preview database.

Usage: uv run scripts/query_db.py [--preview]
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    config = json.loads((ROOT / "wrangler.jsonc").read_text())
    if "--preview" in sys.argv[1:]:
        binding = config["previews"]["d1_databases"][0]
    else:
        binding = config["d1_databases"][0]
    result = subprocess.run(
        ["cf", "d1", "query", binding["database_id"], "--sql", "SELECT * FROM ping ORDER BY id"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"error: cf d1 query failed: {result.stderr.strip()}")
    try:
        statements = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        sys.exit(f"error: cf d1 query did not return JSON: {e}")
    rows = [row for statement in statements for row in statement["results"]]
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
