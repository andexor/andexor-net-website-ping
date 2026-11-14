# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Andexor Network, Inc.
# Author: Ed Jenkins <ed@andexor.net>

"""Create a Cloudflare Account API token for deploying this Worker.

The token has these permissions, no IP filtering, and expires in one year:
  - Account > Workers Scripts > Read, Edit
  - Zone > Workers Routes > Edit, limited to the andexor.net zone

Uses the cf CLI, so the logged-in profile must be allowed to create tokens (the
"API Tokens: Edit" permission, or an account owner login). Permission group ids are
looked up by name at run time, so nothing is hard-coded.

The new token value is printed to stdout once and nowhere else, so it can be piped, for example:
  uv run scripts/create_token.py | gh secret set CLOUDFLARE_API_TOKEN --repo andexor/andexor-net-website-ping
All status messages go to stderr.

Usage: uv run scripts/create_token.py [--name NAME] [--dry-run]
The account id comes from CLOUDFLARE_ACCOUNT_ID, or from cf when the login sees exactly one account.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ZONE_NAME = "andexor.net"
ACCOUNT_SCOPE = "com.cloudflare.api.account"
ZONE_SCOPE = "com.cloudflare.api.account.zone"
# The API calls "Edit" in the dashboard "Write".
ACCOUNT_PERMISSIONS = ["Workers Scripts Read", "Workers Scripts Write"]
ZONE_PERMISSIONS = ["Workers Routes Write"]


def log(message: str) -> None:
    print(message, file=sys.stderr)


def cf(*args: str) -> object:
    result = subprocess.run(["cf", *args], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"error: cf {' '.join(args[:3])} failed: {result.stderr.strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def account_id() -> str:
    from_env = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if from_env:
        return from_env
    accounts = cf("accounts", "list") or []
    if len(accounts) != 1:
        sys.exit("error: set CLOUDFLARE_ACCOUNT_ID (cf sees %d accounts)" % len(accounts))
    return accounts[0]["id"]


def zone_id() -> str:
    zones = [z for z in cf("zones", "list", "--name", ZONE_NAME) or [] if z["name"] == ZONE_NAME]
    if not zones:
        sys.exit(f"error: zone {ZONE_NAME} not found")
    return zones[0]["id"]


def permission_groups(names: list[str], scope: str, groups: list[dict]) -> list[dict]:
    found = []
    for name in names:
        match = [g for g in groups if g["name"] == name and scope in g.get("scopes", [])]
        if not match:
            sys.exit(f"error: permission group not found: {name} ({scope})")
        found.append({"id": match[0]["id"]})
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", default="test", help="token name (default: test)")
    parser.add_argument("--dry-run", action="store_true", help="validate only, create nothing")
    args = parser.parse_args()

    account = account_id()
    zone = zone_id()
    groups = cf("accounts", "tokens", "permission-groups", "list") or []
    expires_on = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")

    policies = [
        {
            "effect": "allow",
            "permission_groups": permission_groups(ACCOUNT_PERMISSIONS, ACCOUNT_SCOPE, groups),
            "resources": {f"com.cloudflare.api.account.{account}": "*"},
        },
        {
            "effect": "allow",
            "permission_groups": permission_groups(ZONE_PERMISSIONS, ZONE_SCOPE, groups),
            "resources": {f"com.cloudflare.api.account.zone.{zone}": "*"},
        },
    ]

    command = [
        "accounts", "tokens", "create",
        "--name", args.name,
        "--expires-on", expires_on,
        "--policies", json.dumps(policies),
    ]  # fmt: skip
    if args.dry_run:
        log(f"Dry run: would create token {args.name}, expires {expires_on}")
        cf(*command, "--dry-run")
        return

    result = cf(*command)
    value = (result or {}).get("value")
    if not value:
        sys.exit("error: the response had no token value")
    log(f"Created token {args.name}, expires {expires_on}. The value is printed once, below.")
    print(value)


if __name__ == "__main__":
    main()
