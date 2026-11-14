# Data Model: Capture More Request Headers

Table `ping`. The DDL lives in `schema.sql` and describes the full table. Existing databases get
the six new columns from `scripts/migrate_db.py`.

| Column | Type | Source | Indexed |
|---|---|---|---|
| `id` | INTEGER | primary key, autoincrement | primary key |
| `received_at` | TEXT NOT NULL | UTC ISO 8601 with milliseconds and `Z`, set by the Worker | yes |
| `referer` | TEXT | request header `Referer` | yes |
| `ping_from` | TEXT | request header `Ping-From` | yes |
| `ping_to` | TEXT | request header `Ping-To` | yes |
| `cf_connecting_ip` | TEXT | request header `CF-Connecting-IP` | no |
| `cf_ipcountry` | TEXT | request header `CF-IPCountry` | no |
| `cf_ray` | TEXT | request header `CF-Ray` | no |
| `host` | TEXT | request header `Host` | no |
| `user_agent` | TEXT | request header `User-Agent` | no |
| `x_real_ip` | TEXT | request header `X-Real-IP` | no |

## Rules

- "A header that is absent is stored as NULL" (FR-002). Passed to D1 as an explicit `jsnull`
  (base research R3).
- "A header that is present is stored exactly as received, with no trimming or validation".
- "Identical rows are allowed".
- The four existing indexes stay and no index is created for the six new columns (FR-004).
- Existing rows keep their values and get NULL in the six new columns.

## Stored header set

The nine headers above (the three existing and the six new), as one constant in `src/worker.py`.
The log object holds exactly these headers when they are present on the request (FR-005, FR-006).
