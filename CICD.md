# How to setup the CI/CD pipeline in GitHub and Cloudflare.

This is the record of the CI/CD, preview, and repository-protection setup for
`andexor-net-website-ping` (a Python FastAPI Cloudflare Worker with a D1 database). It was adapted
from the setup built for `andexor-net-website-contact-us`, and it is written so the same setup can
be copied to other repos. The goal throughout: a bad change must never reach production, and nothing
should depend on a manual step that gets forgotten.

Names and endpoints come from the specs under `specs/`. If they change there, change them here.

## Manual checklist

The manual steps are in [MANUAL-TASKS.md](./MANUAL-TASKS.md), batched into Step 1 (before the first
pull request) and Step 2 (after the workflow has run once). Everything else is automated.

## The pipeline in one picture

```
Pull request          -> deploy to the preview Worker -> smoke test (health + real POST) -> required check
Merge to main         -> deploy to the preview Worker -> smoke test -> deploy to production -> health check
```

Production only deploys after a preview deployed and passed. A pull request can only be merged if
the preview check passed.

## 1. GitHub

### GitHub Actions workflow (`.github/workflows/ci.yml`)
- Runs on `pull_request` and `push` to `main`.
- **Job `Preview and smoke test`**: installs Node, uv, and dependencies, runs
  `uv run pywrangler preview --name preview`, then smoke tests the preview.
  - Health check: `GET /api/v1/ping/health`, with retries (10 tries, 3 seconds apart) because a
    fresh deploy can take a few seconds to answer. It must return 200 with `"ok": true`.
  - Real API call: a `POST /api/v1/ping` with test `Ping-From`, `Ping-To`, and `Referer` headers
    that write a row to the preview database. The service returns 204 with no body, so the job
    fails unless the status is exactly 204. The status and headers are printed. This call is
    never retried and never made against production.
- **Job `Deploy to production`**: `needs: preview`, runs only on a push to `main`. Deploys with
  `uv run pywrangler deploy`, then does a health check (GET only) on
  `https://andexor.net/api/v1/ping/health`.
- **One shared preview.** Every run deploys to the preview named `preview` (the `PREVIEW_NAME`
  setting), so previews never pile up. A job-level `concurrency` group (`preview-environment`,
  no cancelling) makes runs take turns, so a smoke test never runs against a preview that another
  run just overwrote.
- Actions are pinned to exact versions, all older than a week (matches the repo's uv
  `exclude-newer = "1 week"` habit).

### Secrets
Two repository secrets, set under Settings > Secrets and variables, in **both** the Actions list
and the Dependabot list (Dependabot PRs get their own secret store, and without it every Dependabot
PR fails the required check):
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

### Ruleset on the default branch (`andexor-default-ruleset`)
- Blocks deleting `main` and force pushes.
- Requires a pull request. Required approvals: 0. Code owner review and conversation resolution
  are required, stale reviews are dismissed on push, and only merge commits are allowed.
- **Requires the status check `Preview and smoke test`** from the GitHub Actions app
  (integration id 15368). This is what makes the preview a real gate.
- Requires branches to be up to date before merging.
- Bypass: the `admins` team, always. Do not use the merge override to get around a red check.
- A ruleset is changed through the API with `gh api -X PUT repos/andexor/andexor-net-website-ping/rulesets/<id>
  --input file.json`. The required check name must match the job name exactly. A repo's legacy
  branch protection API (`/branches/main/protection`) returns 404 when only a ruleset is used,
  so check `/rulesets` and `/rules/branches/main` instead.

### Dependabot
`.github/dependabot.yml` has the `uv` ecosystem enabled. Dependabot PRs run the same preview check
(they pass because the secrets were added to Dependabot's secret list). After one merge, the other
open PRs go out of date and need `@dependabot rebase` or "Update branch".

### Working conventions
- Every issue I create is assigned to `ejenkins`.
- Every PR I create is assigned to `ejenkins` and requests review from the `andexor/write` team.
- Merge method is a merge commit (the only one the ruleset allows).

## 2. Cloudflare

### API token for CI
Account API token, limited to this account, with:
- Account > Workers Scripts > Edit
- Zone > Workers Routes > Edit, limited to the `andexor.net` zone (zone id
  `2826c1aa23954fa65dd22d0aefca885a`; the deploy re-applies the route `andexor.net/api/v1/ping*`)

No D1 permission is needed, because deploying a Worker with a D1 binding needs none, and CI never
creates or queries the database directly. Set an expiry. Do not use IP filtering (runner IPs change).

### Worker Previews (open beta)
- `preview_urls: true` in `wrangler.jsonc` turns on preview URLs for the Worker. The setting is
  applied to the Worker by a deploy or `wrangler triggers deploy`, and verified with
  `cf workers get <id>` (`subdomain.previews_enabled`).
- A `previews` block in `wrangler.jsonc` gives previews their own vars (`ALLOWED_ORIGINS`) and
  their own D1 binding. Previews do not inherit production settings.
- **A separate preview database**, `andexor-net-website-ping-prev`, shared by all previews, so
  test data never touches production (`andexor-net-website-ping-prod`).
- Preview URL: `https://<preview-name>-<worker-name>.<account subdomain>.workers.dev`. Here that is
  `https://preview-andexor-net-website-ping.andexor.workers.dev`.
- Cloudflare adds `X-Robots-Tag: noindex` to workers.dev preview URLs automatically, so previews
  are not indexed. The production route is unaffected. Previews are still public. Custom-domain
  preview URLs do not get the noindex header, so add it yourself if you ever use them.
- Workers Builds (Cloudflare's own Git integration) must be **disconnected**. It auto-creates a
  build trigger per branch with broken default commands (`uv run build`, `npx wrangler preview`),
  which fail with "Failed to spawn: build". Actions replaces it. If Workers Builds and Actions are
  both on, every push to `main` deploys twice.
- There is no command that lists all previews. Delete one by name with
  `cf previews delete <name> --worker andexor-net-website-ping --force`. Cloudflare keeps up to 100
  previews per Worker on the free plan and removes the least recently used one at the limit.

### Logs
Observability and traces are enabled in `wrangler.jsonc`. The Worker's logs hold the error detail
(the error name and description, per the constitution's error rule), and one line with the stored request headers
for every ping. CI output only says that a call failed and with which status.

## 3. This repo

| File | What it does |
|---|---|
| `.github/workflows/ci.yml` | The pipeline above. |
| `.github/dependabot.yml` | Dependabot updates for `uv`. |
| `wrangler.jsonc` | Route, `preview_urls`, the `previews` block (vars and preview D1 binding), logs and traces. Must be plain JSON, with no comments, for the scripts to edit it. |
| `schema.sql` | `CREATE TABLE IF NOT EXISTS ping (...)`, applied to the preview and production databases. |
| `preview-create.sh` | Creates the preview database, applies `schema.sql`, writes the `previews` block, and reports whether preview URLs are on. `--enable-preview-urls` turns them on. Idempotent. |
| `preview-delete.sh` | Decommissions the preview environment: previews, the preview database, and the config block. Asks for confirmation unless `--yes`. `--preview NAME` deletes one preview. Refuses to touch the production database. |
| `preview-test.sh` | Deploys a preview by hand and runs the same health check and POST as CI. |
| `health.sh` | Health check against the preview and production. |
| `deploy.sh` | Production deploy by hand, then a database warm-up with `scripts/query_db.py`. |
| `scripts/create_db.py` | Creates the production database and table, and writes `database_id` into `wrangler.jsonc`. |
| `src/worker.py` | CORS for the allowed origins, plus error handling: each step that can fail has its own inline try/except that logs the step, error name, description, and source line, and returns a JSON `{"ok": false}` with a 500. |
| `README.md`, `setup.md` | Document the preview scripts and URLs. |

### Design decisions
- **`/health` is liveness only.** It does not test the database or any other dependency, so a
  dependency problem cannot cascade into a failing health check. The database is exercised by the
  preview smoke test's real POST instead.
- **A successful ping returns 204 with no body**, so the smoke test checks the status code only.
  The row it writes is the proof the database binding works, and a failed insert returns 500.
- **Error details stay in the service logs.** Responses carry only `{"ok": false}`. No
  per-environment behavior.
- **Create and delete are scripted from day one.** There is a committed script to build every
  environment and one to tear it down, so decommissioning is never a manual dashboard hunt.
- **Names come from the config**, not hard-coded, so the scripts copy to other projects.

## 4. Proof the gate works

Run this once on a throwaway PR after the ruleset exists: put a wrong table name in the insert,
and confirm the health check passes, the POST returns 500, `Preview and smoke test` goes red,
`Deploy to production` is skipped, and the PR shows as blocked. Revert the change and confirm it
turns green. Done on throwaway PR #3 (2026-11-14): health passed, the POST returned 500, the check went red, production deploy was skipped, the PR was BLOCKED, and the revert turned it green.

## 5. Checklist for another repo

1. Copy `.github/workflows/ci.yml`. Change the Worker name source, the account workers.dev
   subdomain (`WORKERS_SUBDOMAIN`), the health path, and the smoke test's POST headers.
2. Add `preview_urls` and a `previews` block to `wrangler.jsonc`, with its own preview D1 database.
   Copy `preview-create.sh` and `preview-delete.sh` and run `preview-create.sh`.
3. Create the Cloudflare API token (permissions above) and add `CLOUDFLARE_API_TOKEN` and
   `CLOUDFLARE_ACCOUNT_ID` to the Actions secrets and the Dependabot secrets.
4. Turn on preview URLs once: `./preview-create.sh --enable-preview-urls`.
5. Disconnect Workers Builds for the repo, or at least make sure it cannot deploy `main`.
6. Open a PR with the workflow so it runs once. A required check only appears in the ruleset picker
   after it has run.
7. Create the ruleset on the default branch with the rules in section 1, including the required
   `Preview and smoke test` check.
8. Copy `.github/dependabot.yml` if you want dependency PRs.
9. Run the negative test (break the smoke test on a throwaway PR, confirm it blocks, revert).
10. Delete any old previews by name.

## 6. Pitfalls found along the way

- Workers Builds auto-creates a per-branch trigger with stale default commands, and GitHub's Retry
  button re-uses the commands recorded on the old build.
- `curl --fail` discards the response body on an error. Use `--write-out '%{http_code}'` and print
  the body instead.
- Previews named after PRs and commits pile up. Use one fixed name and serialize runs.
- `wrangler preview` needs a `previews` block, and previews do not inherit production settings.
- Preview URLs stay off until the Worker-level setting is applied once.
- An unhandled error used to produce a plain-text 500 and no log line. Guard each step that can fail with its own inline try/except that logs the step, error, and line.
- When a PR has a pending review request, the auto-mode classifier blocks a merge as "Merge
  Without Review". Say so in chat first.
- A VS Code file rename is not a `git mv`. Rename with git so history follows.

## 7. API Tokens

### CLOUDFLARE_API_TOKEN

Within a repo, the same CLOUDFLARE_API_TOKEN should be used for both Actions and Dependabot.
But every repo needs to have a unique Account API token
(CLOUDFLARE_API_TOKEN) that is different from all other repos.

### CLAUDE_CODE_OAUTH_TOKEN

If a build ever fails and mentions CLAUDE_CODE_OAUTH_TOKEN,
it probably expired. Do this to get a new token:

#### Get a new token.

> `claude setup-token`

#### Update the value in the repo's secrets. Paste in the new token when prompted.

> `gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo andexor/andexor-net-website-ping`

#### Update the job id and re-run the failed step.

> `gh run rerun <id> --failed`
