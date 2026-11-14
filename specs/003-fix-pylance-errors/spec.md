# Feature Specification: Fix Pylance Type Errors

**Feature Branch**: `7-fix-pylance-errors`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User description: "Fix the 20 Pylance type errors reported in src/worker.py (GitHub issue #7). Behavior must not change." 

This feature amends `specs/001-click-ping-logging/` and `specs/002-capture-request-headers/`. It changes
no behavior. It only makes the service source type-clean.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open the service source with no reported problems (Priority: P1)

As the maintainer, I want the editor's type checker to report zero problems for the service source, so
that any new problem it reports is a real signal and is not lost among known ones.

**Why this priority**: This is the whole purpose of the feature. Twenty standing errors hide new ones.

**Independent Test**: Open the service source in the editor with the type checker at the project's
configured strictness. Confirm the problem count is 0.

**Acceptance Scenarios**:

1. **Given** the service source before this feature, **When** it is checked, **Then** 20 errors are reported.
2. **Given** the service source after this feature, **When** it is checked, **Then** 0 errors and 0 warnings are reported.

---

### User Story 2 - Behavior stays exactly the same (Priority: P1)

As the site owner, I want the service to respond and log exactly as it did before, so that fixing the
type problems cannot break click logging.

**Why this priority**: A type clean-up that changes behavior would be a regression in a live service.

**Independent Test**: Run the health check and the preview smoke test, then force each failure step and
compare the log line and response with those before the change.

**Acceptance Scenarios**:

1. **Given** a valid ping, **When** it reaches the service, **Then** the response is 204 with no body and one record is stored, as before.
2. **Given** a failure at any step, **When** it occurs, **Then** the log line is `ping_error step=<step> error=<ErrorName>: <description> line=<n>` and the response is 500 with `{"ok": false}`, as before.
3. **Given** any request, **When** it is answered, **Then** the CORS headers are the same as before.

### Edge Cases

- A failure whose traceback is not available: the log line must still be written and the 500 response still returned (the ` line=<n>` part is omitted from the log line, and no placeholder such as `line=0` is written).
- The check must not be satisfied by switching the type checker off or by blanket suppression comments.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service source MUST produce 0 errors and 0 warnings from the project's type checker.
- **FR-002**: Every function parameter and return value in the service source MUST have a known type.
- **FR-003**: Responses, status codes, CORS headers, and stored data MUST be unchanged.
- **FR-004**: The error log line format MUST be unchanged, including `line=<n>` whenever a traceback is available. When it is not, ` line=<n>` is omitted entirely.
- **FR-005**: Each statement that can raise an error MUST keep its own inline try/except with no shared helper or catch-all handler (constitution, Principle IV).
- **FR-006**: The fix MUST NOT disable type checking rules or use blanket suppression comments.
- **FR-007**: No new runtime dependency MAY be added.

### Key Entities

None. No data changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The type checker reports 0 problems for the service source, down from 20.
- **SC-002**: The preview smoke test (health check and one ping) passes unchanged.
- **SC-003**: For each of the six error steps, the log line and response match those before the change.

## Assumptions

- "The project's type checker" is the editor's Pylance at the strictness the maintainer currently uses, which reports unknown types as errors.
- The service source is `src/worker.py`. Scripts under `scripts/` are not in scope.
- The fix may add type annotations and handle a missing traceback inline; how is left to planning.
