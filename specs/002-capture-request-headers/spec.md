# Feature Specification: Capture More Request Headers

**Feature Branch**: `4-capture-request-headers`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User description: "Add these headers to the data model and capture them from the request headers: cf-connecting-ip, cf-ipcountry, cf-ray, host, user-agent, x-real-ip. Then update the logging to only include headers that are written to the database. Exclude all other headers from the log implicitly. Do not add indexes for these new fields yet." (GitHub issue #4)

This feature amends `specs/001-click-ping-logging/`, which stays the base specification. Where the two
disagree, this specification wins. The amended items are listed under "Changes to the base
specification" below.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Store more details about each click (Priority: P1)

As an SRE, I want each ping record to also hold the visitor's network address, country, request
identifier, requested host, and browser identification, so that I can tell interactive use from
non-interactive use by looking at who sent the ping and how, and so that I can match a record to
Cloudflare's own logs.

A ping arrives. As well as the arrival time, referrer, link source, and link target, the service now
stores six more details taken from the request: the connecting client address, the client country,
the Cloudflare request identifier, the host the request was sent to, the browser identification, and
the forwarded real client address.

**Why this priority**: This is the whole purpose of the feature. The details are needed to decide
what the service should keep in the long run.

**Independent Test**: Send one ping that carries all six new headers. Confirm exactly one new record
exists and that each of the six new fields holds the value that was sent. Then send a ping that
carries none of them and confirm the six fields are empty (NULL).

**Acceptance Scenarios**:

1. **Given** a ping that carries `cf-connecting-ip`, `cf-ipcountry`, `cf-ray`, `host`, `user-agent`,
   and `x-real-ip`, **When** it reaches the service, **Then** one record is stored in which each of
   the six new fields holds the value of the matching header, exactly as received.
2. **Given** a ping that is missing some or all of the six headers, **When** it reaches the service,
   **Then** a record is still stored, and each missing detail is stored as empty (NULL).
3. **Given** two pings with identical details, **When** both reach the service, **Then** two
   separate records are stored.
4. **Given** a ping that carries all the details the service stored before this feature, **When** it
   reaches the service, **Then** the arrival time, referrer, link source, and link target are stored
   exactly as before.

---

### User Story 2 - Log only what is stored (Priority: P1)

As the site owner, I want the service log to hold only the headers that are written to the
database, so that sensitive headers such as `Cookie` and `Authorization` are no longer written to
the log.

**Why this priority**: The earlier decision to log every header was meant for a short period of
initial testing. This feature ends it, and the log holds personal and sensitive data until it does.

**Independent Test**: Send one ping that carries the stored headers plus `Cookie`, `Authorization`,
and a made-up header. Confirm the log line for that ping holds the stored headers and none of the
three others.

**Acceptance Scenarios**:

1. **Given** a ping with any headers, **When** it reaches the service, **Then** the service log
   holds one JSON object, without added escape characters, whose names and values are those of the
   request headers that are stored in the database, and no others.
2. **Given** a ping that carries `Cookie`, `Authorization`, or any header that is not stored,
   **When** it reaches the service, **Then** those headers do not appear anywhere in the service log.
3. **Given** a header is added to the stored set in a later change, **When** that change is made,
   **Then** the log picks it up from the same list that decides what is stored, so the log and the
   database cannot drift apart.

---

### User Story 3 - Add the new fields to existing data stores (Priority: P2)

As a maintainer, I want the new fields to be added to the existing preview and production data
stores without losing records, so that the service can be deployed without recreating them.

**Why this priority**: Both data stores already exist and hold records. Without this, the first
ping after deploy fails.

**Independent Test**: On a data store that holds records created before this feature, run the
update. Confirm the old records are intact with the new fields empty, and that running the update a
second time changes nothing and does not fail.

**Acceptance Scenarios**:

1. **Given** a data store with the earlier record structure, **When** the update runs, **Then** the
   six new fields exist, existing records are unchanged, and their new fields are empty (NULL).
2. **Given** a data store that already has the new fields, **When** the update runs again, **Then**
   it succeeds and changes nothing.
3. **Given** a new, empty data store, **When** the update runs, **Then** it ends up with the full
   record structure.
4. **Given** the new fields were added, **When** the stored indexes are listed, **Then** they are
   the same indexes as before this feature, and none cover the new fields.

---

### Edge Cases

- A ping that carries none of the nine stored headers is still recorded, with an arrival time, and
  its log line is an empty JSON object.
- A header sent more than once, or with an empty value, is stored as received by the same rule as
  the existing headers. Nothing is trimmed, validated, or rejected.
- Header names are matched without regard to letter case, as for all headers.
- Very long browser identification values are stored as received.
- If the data store has not yet been updated when the new service version is deployed, pings fail
  with the standard failure answer and the failure is logged. The deployment order in the
  assumptions below prevents this.
- Pings that arrive directly, not through Cloudflare, may lack the Cloudflare headers. Those fields
  are then empty.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For each ping the service MUST also store these request headers in new optional
  fields: `cf-connecting-ip` as `cf_connecting_ip`, `cf-ipcountry` as `cf_ipcountry`, `cf-ray` as
  `cf_ray`, `host` as `host`, `user-agent` as `user_agent`, and `x-real-ip` as `x_real_ip`.
- **FR-002**: A header that is absent MUST be stored as empty (NULL). A header that is present MUST
  be stored exactly as received, with no trimming or validation. Identical records MUST NOT be
  merged or rejected.
- **FR-003**: The existing fields (arrival time, `referer`, `ping_from`, `ping_to`) and their
  behavior MUST NOT change.
- **FR-004**: The new fields MUST NOT be indexed. The indexes that existed before this feature MUST
  stay unchanged.
- **FR-005**: The service log entry for each ping MUST be one JSON object, without added escape
  characters, that holds only the request headers that are stored in the database (the three
  existing ones and the six new ones), under their header names. Every other request header,
  including `Cookie` and `Authorization`, MUST be excluded from the log.
- **FR-006**: The set of logged headers MUST be derived from the set of stored headers, so that a
  header cannot be logged without being stored, and the exclusion of all other headers is implicit,
  not a list of names to remove.
- **FR-007**: The record structure definition committed in the repository MUST describe the full
  record, including the six new fields, and MUST still create a complete structure on an empty data
  store.
- **FR-008**: A committed script MUST add the new fields to an existing data store (preview or
  production). It MUST be safe to run more than once, MUST NOT lose or change existing records, and
  MUST read names from the configuration.
- **FR-009**: Failure handling, the answers returned, the CORS behavior, the health address, and the
  preview and production pipeline MUST NOT change. Each new step that can fail MUST be guarded
  individually as required by FR-011 of the base specification.
- **FR-010**: The preview test ping in the pipeline and in `preview-test.sh` MUST keep returning
  HTTP 204, and the record it writes MUST be readable with `scripts/query_db.py`, which MUST print the
  new fields as well.

### Key Entities

- **Ping record**: Gains six optional attributes: client address, client country, request
  identifier, requested host, browser identification, and forwarded client address. Existing
  attributes are unchanged.
- **Stored header set**: The nine request headers that are written to the database. It is the single
  source for both the stored fields and the logged headers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a ping that carries all nine stored headers, 100% of the nine values appear in the
  stored record exactly as sent.
- **SC-002**: For a ping that carries `Cookie`, `Authorization`, and an unlisted header, 0 of those
  header names or values appear in the service log.
- **SC-003**: After the update runs on an existing data store, 100% of the records that existed
  before it are unchanged, and a second run changes nothing.
- **SC-004**: The number of indexes on the record table is the same after this feature as before it.
- **SC-005**: The preview health check and test ping still pass, and a change with this feature
  reaches production only through the same gate as any other change.

## Assumptions

- This feature ends the base specification's temporary decision to log every request header. From
  now on the log holds only stored headers. Existing log entries are not changed, and they expire on
  the 7-day retention schedule of the account's plan.
- Even with the shorter log, the log and the data store now hold client addresses and browser
  identification. They are to be treated as personal data, and the retention and reporting rules of
  the base specification are unchanged.
- A header that is stored but absent from a request is left out of the log object, not logged as
  empty. The log shows what the request carried.
- The log keys are the header names in lower case, as the service receives them.
- No indexes are added for the new fields now. They are added by a later change if the owner decides
  to query by them.
- The data store update runs on the preview store before the new service version is deployed to
  preview, and on the production store before the merge that deploys to production. The update only
  adds fields, so the previous service version keeps working against the updated store.
- `host` is stored even though it is usually `andexor.net`. It tells apart pings that came by other
  routes.
- Unit and functional tests, validation, authentication, rate limiting, and notifications remain out
  of scope.

## Changes to the base specification

These items of `specs/001-click-ping-logging/spec.md` are amended by this feature and are to be
updated in the same pull request:

- FR-005 ("Every stored column MUST be searchable efficiently"): the six new columns are not indexed.
- FR-006 (log the names and values of all request headers): replaced by FR-005 above.
- User Story 1, acceptance scenario 4, and the first assumption (log every header, including
  `Cookie` and `Authorization`): replaced by User Story 2 above.
- Key entity "Ping record": gains the six attributes.
