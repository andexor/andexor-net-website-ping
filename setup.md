<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 Andexor Network, Inc.
Author: Ed Jenkins <ed@andexor.net>
-->

# Install Pre-requisites

Most projects have certain pre-requisites that are required for development, testing, or running in production. Install the ones that are needed.

## NodeJS

Some tools might require NodeJS.

The following script was copied from
[Node.js — Download Node.js®](https://nodejs.org/en/download/current).

### Download and install nvm:

> `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh | bash`<br/>
> `exit`

### Start a new shell and download and install Node.js:

> `nvm install 26`

### Verify the Node.js version:

> `node -v`

### Verify npm version:

> `npm -v`

### Upgrade to the latest Node

> `nvm use --lts`

## Spec Kit

Some projects use Spec Kit to manage feature requirements and development.

If you have not installed uv yet, install it first.

> Run `install-uv.sh`<br/>
> Run `install-spec-kit.sh`

## Cloudflare Workers

This service is deployed to Cloudflare Workers.

If you do not have Cloudflare installed and integrated with Claude Code,
then open Claude Code and paste this text into the prompt.

> Fetch and execute the appropriate instructions<br/>
> to set me up for Cloudflare from<br/>
> https://developers.cloudflare.com/agent-setup/prompt.md

Then log in. Use the browser-callback flow, not the default device-code flow.

> Run `cf auth login --no-device`

## Install dependencies

> Run `uv sync`

## Create the production database

This only needs to be done once. It creates the D1 database `andexor-net-website-ping-prod`,
creates the `ping` table from `schema.sql`, and writes the `database_id` into `wrangler.jsonc`.
Commit the change to `wrangler.jsonc`.

> Run `uv run scripts/create_db.py`

## Create the preview environment

This only needs to be done once.

> Run `preview-create.sh`

## Delete the preview environment

This is not to be done for every test.
The environment should remain as long as the production environment remains.
This script is only provided in case decommissioning is needed later.

> Run `preview-delete.sh`

## Test the preview environment

This may be done anytime a test is needed.

> Run `preview-test.sh`

## Run locally

This runs the Worker with `pywrangler preview`. It is not a local-only server,
so it needs the preview database from "Create the preview environment".

> Run `run.sh`

## Deploy to production

CI deploys production after a merge to `main`. See [CICD.md](./CICD.md).
This script is for a manual deploy. It also warms up the database connection.

> Run `deploy.sh`

## Check health

Checks the preview and production health endpoints.

> Run `health.sh`

## Add new columns to an existing database

A database made by `create_db.py` or `preview-create.sh` already has every column. For a database
made earlier, this adds the columns that are missing and changes nothing else. It is safe to run
more than once. Add `--preview` for the preview database.

> Run `uv run scripts/migrate_db.py`

## View the logged pings

Prints every row in the production table as JSON. Add `--preview` for the preview table.

> Run `uv run scripts/query_db.py`
