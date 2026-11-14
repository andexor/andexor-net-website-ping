# Data Model: Click Ping Logging

One table, `ping`, in each of the two D1 databases (preview and production). The definition is
`schema.sql` at the repo root and is applied with `CREATE ... IF NOT EXISTS`.

## Ping record (table `ping`)

| Column | Type | Required | Source |
|---|---|---|---|
| `id` | INTEGER, primary key, autoincrement | Yes | Database |
| `received_at` | TEXT | Yes | The Worker: UTC, ISO 8601 with milliseconds and `Z` |
| `referer` | TEXT | No | Request header `Referer` |
| `ping_from` | TEXT | No | Request header `Ping-From` |
| `ping_to` | TEXT | No | Request header `Ping-To` |

**Rules**
- A header that is absent is stored as NULL. A header that is present is stored exactly as received,
  with no trimming or validation (FR-016).
- Rows are never updated or deleted by the service. Identical rows are allowed (FR-004).
- Indexes, all non-unique: `received_at`, `referer`, `ping_from`, `ping_to` (FR-005). `id` is
  indexed as the primary key.
- No relationships to other tables. No state transitions.

## Environment

| Environment | Database | Allowed origins source |
|---|---|---|
| Production | `andexor-net-website-ping-prod` | `vars.ALLOWED_ORIGINS` |
| Preview | `andexor-net-website-ping-prev` | `previews.vars.ALLOWED_ORIGINS` |

Records never move between databases. The scripts refuse to treat the two as the same database.

## Changing the model

New columns start in the spec. `ALTER TABLE` statements are not in `schema.sql`, so adding a column
needs a one-time change to both databases and a matching update to `schema.sql`.
