# Feature Specification: Click Ping Logging

**Feature Branch**: `1-write-prd`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User description: "Seed from PRD.md: write the feature spec for the Andexor Ping Service (log link clicks from andexor.net via the HTML anchor ping attribute to Cloudflare D1; POST/OPTIONS /api/v1/ping, GET /api/v1/ping/health; CORS; error handling; preview and production environments). PRD.md is only a seed. The spec becomes the source of truth."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record a link click (Priority: P1)

As an SRE, I want every interactive click on a link at https://andexor.net/ to leave a record, so
that I can count clicks and compare them to page views to tell interactive use from
non-interactive use.

A visitor clicks a link. The browser automatically sends a ping to the service because the link
lists the service address in its `ping` attribute. The service records when the ping arrived, which
page the click came from, and where the link points. The visitor sees nothing and is never delayed.

**Why this priority**: This is the whole purpose of the service. Without it nothing can be counted.

**Independent Test**: Send one ping to the service with a link source and a link target. Confirm
the service answers with success and no content, and that exactly one new record exists with the
arrival time, referrer, link source, and link target filled in.

**Acceptance Scenarios**:

1. **Given** a ping from a visitor's browser carrying a link source and a link target, **When** it
   reaches the service, **Then** the service answers with success and no content, and one record is
   stored with the arrival time (UTC), referrer, link source, and link target.
2. **Given** a ping that carries only some of the optional details, **When** it reaches the
   service, **Then** a record is still stored, with the missing details left empty.
3. **Given** two pings with identical details, **When** both reach the service, **Then** two
   separate records are stored.
4. **Given** any ping, **When** it reaches the service, **Then** the names and values of every
   header on the request are written to the service log as one JSON object, without added escape
   characters.

---

### User Story 2 - Pings are accepted from the website only (Priority: P2)

As the site owner, I want browsers to be allowed to send pings from the website, and from a local
development copy of it, so that clicks are recorded in real use and during development.

**Why this priority**: Without it browsers can refuse to send pings from the site, so P1 would not
work in real use. It is secondary because the service itself works without it.

**Independent Test**: Send a preflight request with the website origin, then with an unlisted
origin. Confirm the allowed-origin answer echoes the website origin in the first case and falls
back to the first listed origin in the second.

**Acceptance Scenarios**:

1. **Given** a preflight request from `https://andexor.net`, **When** it reaches the service,
   **Then** the service answers with success and no content, and the answer allows that origin for
   the POST and OPTIONS methods and the `Content-Type` header.
2. **Given** a request from `http://localhost:8787`, **When** it reaches the service, **Then** that
   origin is allowed in the same way.
3. **Given** a request from an origin that is not on the allowed list, **When** it reaches the
   service, **Then** the answer names the first allowed origin instead, so the browser refuses the
   request.
4. **Given** any answer, **When** the allowed origin depends on the request origin, **Then** the
   answer says so, so that caches keep separate copies.

---

### User Story 3 - Check that the service is alive (Priority: P2)

As an operator, I want a health address that tells me the service is answering, so that deployment
checks and smoke tests can confirm a deploy took effect.

**Why this priority**: The deployment gate depends on it, but it records no clicks itself.

**Independent Test**: Request the health address. Confirm a success answer with `{"ok": true}`.

**Acceptance Scenarios**:

1. **Given** the service is running, **When** its health address is requested, **Then** the answer
   is success with the body `{"ok": true}`.
2. **Given** the database is unavailable, **When** the health address is requested, **Then** the
   answer is still success, because health reports only that the service is answering.

---

### User Story 4 - Failures are visible to operators but not to visitors (Priority: P2)

As an operator, I want every failure to be logged with its name and description, so that I can find
the cause, while callers learn only that the request failed.

**Why this priority**: It makes problems diagnosable. It is secondary to recording clicks.

**Independent Test**: Make a ping fail (for example, by sending it to a copy of the service whose
database is missing). Confirm the caller gets a failure answer with `{"ok": false}` and no error
detail, and that the service log holds the error name and description.

**Acceptance Scenarios**:

1. **Given** a ping that cannot be stored, **When** the failure happens, **Then** the caller gets
   a server-error answer with the body `{"ok": false}`, and the error name and description are
   written to the service log.
2. **Given** any other unexpected failure in the service, **When** it happens, **Then** the same
   logged-and-`{"ok": false}` handling applies. No other handling is performed.

---

### User Story 5 - Test changes without touching real data (Priority: P3)

As a maintainer, I want a preview copy of the service with its own data store, so that a change can
be tested end to end before it reaches the live site, and test records never mix with real clicks.

**Why this priority**: It protects the quality of P1 data over time. It does not add visitor-facing
behavior.

**Independent Test**: Deploy a change to the preview copy, send a test ping, and confirm the record
appears in the preview data store and not in the production data store.

**Acceptance Scenarios**:

1. **Given** a change under test, **When** it is deployed to the preview copy and a test ping is
   sent, **Then** the record is stored in the preview data store only.
2. **Given** a change whose preview health check or test ping fails, **When** the pipeline runs,
   **Then** the change is not deployed to production.
3. **Given** a change whose preview checks pass and that is merged to the main branch, **When** the
   pipeline runs, **Then** it is deployed to production and the production health address answers
   success. The test ping is never sent to production.

### Edge Cases

- A ping with no details at all still produces a record that has an arrival time.
- A ping sent with a body is accepted, and the body is ignored.
- Details are stored as received. Empty, very long, or unusual values are not rejected.
- A request with a method the service does not offer is not recorded.
- The same click may be reported more than once by a browser, which produces more than one record.
  Deduplication is not attempted.
- Automated tests that click links also produce pings. They cannot be told apart from visitors, and
  the service does not try.
- If the data store is unavailable, pings are lost for that period. The caller gets the failure
  answer, and nothing is retried or queued.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST accept a ping at `POST /api/v1/ping` and answer with HTTP 204 and no
  body.
- **FR-002**: For each ping the service MUST store one record containing the arrival time (UTC,
  ISO 8601, set by the service, never by the caller), the request header `Referer`, the request
  header `Ping-From` (link source), and the request header `Ping-To` (link target).
- **FR-003**: Only the identifier and arrival time MUST be required in a record. Referrer, link
  source, and link target MUST be optional. A missing detail MUST be stored as an empty (NULL) value.
- **FR-004**: Each record MUST be stored separately, and identical details MUST NOT be merged or
  rejected.
- **FR-005**: Every stored column MUST be searchable efficiently and MUST allow duplicate values.
- **FR-006**: For each ping the service MUST write the names and values of all request headers to
  the service log as one JSON object, without added escape characters.
- **FR-007**: The service MUST answer a preflight request at `OPTIONS /api/v1/ping` with HTTP 204.
- **FR-008**: The service MUST echo the request's `Origin` in the allowed-origin answer when it is
  on the configured list (`https://andexor.net`, `http://localhost:8787`), and otherwise MUST answer
  with the first entry of the list. The list MUST come from configuration, separately for preview
  and production.
- **FR-009**: Answers MUST allow the POST and OPTIONS methods and the `Content-Type` header, and
  MUST declare that the answer varies by origin.
- **FR-010**: The service MUST offer `GET /api/v1/ping/health`, answering HTTP 200 with
  `{"ok": true}`. It MUST check liveness only and MUST NOT depend on the data store.
- **FR-011**: Each step that can fail MUST be guarded individually, so that a failure in one step
  is reported as that step and no other. A failure MUST be handled by writing a log entry with the
  name of the failing step, the error name, the error description, and the source line, and by
  answering HTTP 500 with `{"ok": false}`. Error detail MUST NOT appear in the answer.
- **FR-012**: The service MUST be reachable on the production site at `andexor.net/api/v1/ping*`.
- **FR-013**: A preview copy MUST exist with its own data store, separate from the production data
  store, with the same behavior as production.
- **FR-014**: The production data store and the preview data store MUST each hold the same record
  structure, created from a single committed definition that can be applied repeatedly.
- **FR-015**: A change MUST reach production only after it has been deployed to the preview copy and
  both of these have succeeded: the preview health check, and a real test ping that returns HTTP 204.
  The test ping MUST NOT be repeated automatically and MUST NOT be sent to production.
- **FR-016**: The service MUST NOT validate pings, authenticate callers, limit rates, check for
  bots, or send notifications.
- **FR-017**: Maintainers MUST be able to create the production data store, create and remove the
  preview environment, and read back all stored records, each with a committed script that is safe to
  run more than once.

### Key Entities

- **Ping record**: One reported link click. Attributes: identifier (required, unique), arrival time
  (required, UTC), referrer (optional), link source (optional), link target (optional). Records are
  independent of each other. More attributes may be added after testing begins.
- **Environment**: Either preview or production. Each has its own address, its own list of allowed
  origins, and its own ping data store. Records never move between environments.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a visitor clicks a tracked link, a record for that click is stored within
  5 seconds, and the visitor notices no delay in reaching the link target.
- **SC-002**: Across a week of normal use, at least 99.9% of pings the service receives result in
  exactly one stored record.
- **SC-003**: An SRE can count clicks for any time range and compare the total to page views
  without handling anything other than the stored records.
- **SC-004**: 100% of failed pings appear in the service log with an error name and description.
- **SC-005**: 0 test records appear in the production data store, and 0 production records appear
  in the preview data store.
- **SC-006**: 0 changes reach production without a passing preview health check and test ping.
- **SC-007**: A new maintainer can create the data stores and the preview environment from the
  repository documents, and the manual steps are listed in one place.

## Assumptions

- During limited initial testing the service logs every request header, including `Cookie`,
  `Authorization`, and client-address headers, on purpose. The logs will be examined by hand to
  decide which other headers belong in the database, and the logging will then be trimmed down.
  Until then, treat the service logs as sensitive. Cloudflare sets the retention of these logs by
  plan and it cannot be configured. The account is on Workers Paid, so logs are kept for 7 days
  (the maximum).
- The website will be changed separately to list the service address in the `ping` attribute of
  its links. That change is out of scope here.
- Browsers send the `Ping-From` and `Ping-To` headers on pings. Browsers that do not support the
  `ping` attribute send nothing, and that traffic is not counted.
- Pings are not authenticated. Anyone can send one, so counts are an indicator and not an exact
  measure.
- Expected traffic is the click rate of a small website, so no special capacity planning is needed.
- Records are kept indefinitely. Retention, reporting screens, and notifications are out of scope.
- The service name is `andexor-net-website-ping`, and it runs on the same domain and Cloudflare
  account as the website.
- The preview copy is created once, ahead of time, as a manual step. The pipeline deploys to it
  but does not create it.
- Automated unit and functional tests are out of scope. The preview test ping is the end-to-end
  check.
- Docker packaging is out of scope.
