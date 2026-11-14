<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 Andexor Network, Inc.
Author: Ed Jenkins <ed@andexor.net>
-->

# Manual Tasks

Everything not listed here is automated by a committed script or by the CI workflow. The manual
work is batched into two steps. Do Step 1 once, before the first pull request. Do Step 2 once,
after the first pull request has run the workflow. Step 3 is a one-time database change for the
request headers feature. Background for each item is in
[CICD.md](./CICD.md).

## Step 1: Before the first pull request

Do all of these together, in this order. The preview Worker item needs `src/worker.py`, so Step 1
cannot finish until the first Worker skeleton exists. The implementation tasks pause at T004 in
`specs/001-click-ping-logging/tasks.md` and wait for you to finish this step.

- [X] **Log in to Cloudflare.** Use the browser-callback flow.
  `cf auth login --no-device`
- [X] **Install dependencies.**
  `uv sync`
- [X] **Create the production database.** Creates the D1 database, applies `schema.sql`, and
  writes `database_id` into `wrangler.jsonc`.
  `uv run scripts/create_db.py`
- [X] **Create the preview environment.** Creates the preview D1 database, applies `schema.sql`,
  and writes the `previews` block. Run it after the production database so the safety check that
  compares the two ids has something to compare. If it reports that preview URLs are OFF, that is
  expected before the Worker exists, and the script does not fail because of it. The next item
  fixes that.
  `./preview-create.sh`
- [X] **Create the preview Worker once, in advance.** The pipeline deploys to the preview but does
  not create it. This needs `src/worker.py`, so do it after the Worker code is on the branch. It
  deploys the preview named `preview` and smoke tests it, then turns on preview URLs.
  `./preview-test.sh`
  `./preview-create.sh --enable-preview-urls`
  Check the preview URL answers: `./health.sh`
- [X] **Commit the `wrangler.jsonc` changes** from the two scripts above (the `database_id` values).
- [X] **Create the Cloudflare API token** in the dashboard (Account API token, unique to this repo,
  with an expiry, no IP filtering):
  - Account > Workers Scripts > Edit
  - Zone > Workers Routes > Edit, limited to the `andexor.net` zone
- [X] **Add the secrets** to `andexor/andexor-net-website-ping`, in **both** Settings > Secrets and
  variables > Actions **and** the Dependabot list:
  - `CLOUDFLARE_API_TOKEN` (the token above)
  - `CLOUDFLARE_ACCOUNT_ID` = `89df54b7a586cd4489e7a8bc6cd5145d`
  - `CLAUDE_CODE_OAUTH_TOKEN`, only if the workflow uses Claude Code (`claude setup-token`)

## Step 2: After the first pull request has run the workflow

Open the first pull request (the one that adds `.github/workflows/ci.yml`). A required check only
appears in the ruleset picker after it has run once. Then do all of these together.

- [X] **Make sure Workers Builds is not connected** to the `andexor-net-website-ping` Worker in the
  Cloudflare dashboard. If it is, disconnect it. Otherwise every push to `main` deploys twice.
- [X] **Create the ruleset** `andexor-default-ruleset` on `main` with the rules in
  [CICD.md](./CICD.md) section 1, including the required check `Preview and smoke test`.
- [X] **Run the negative test** on a throwaway PR, as described in [CICD.md](./CICD.md) section 4,
  and record the PR number there.
- [X] **Delete stray previews** by name, if any exist:
  `cf previews delete <name> --worker andexor-net-website-ping --force`

## Step 3: Database change for the request headers feature (issue #4)

The Worker for this feature writes six new columns. CI cannot add them, because its token has no
D1 permission. The change only adds nullable columns, so the Worker that is in production now
keeps working in between. Do these in order.

- [ ] **Before opening the pull request**, add the columns to the preview database:
  `uv run scripts/migrate_db.py --preview`
- [ ] **Before merging the pull request**, add the columns to the production database. It prints
  which columns it added, and a second run prints that there is nothing to add:
  `uv run scripts/migrate_db.py`
