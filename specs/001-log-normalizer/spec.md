# Feature Specification: Log Normalizer Service

**Feature Branch**: `001-log-normalizer`

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: "Given the contents of README.md and SCHEMA.md, build an application that will accomplish the goals laid out in those documents."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Process RFC 3164 Syslog Logs (Priority: P1)

As a Data Integration Engineer, I want the server to listen on a TCP port, accept RFC 3164 syslog logs, parse their headers and CEF extensions, map them to the normalized schema, and output them as NDJSON so that I can analyze Syslog events in a unified format.

**Why this priority**: Core ingestion requirement. Delivers immediate value by parsing standard security syslog records.

**Independent Test**: Can be tested by running the server, sending `samples/syslog/sample-1.log` via TCP to port 5044, and verifying the mapped NDJSON output on stdout matches the expected fields.

**Acceptance Scenarios**:

1. **Given** the TCP server is running and listening on port 5044, **When** an RFC 3164 Syslog log (e.g. `sample-1.log`) is sent as a single line, **Then** the server outputs a single-line NDJSON record to stdout with the mapped fields `@timestamp`, `event.type`, `event.category`, `event.outcome`, `source.ip`, `user.name`, `host.name`, `log.level`, and `message`.

---

### User Story 2 - Process NDJSON Logs (Priority: P1)

As a Data Integration Engineer, I want the server to accept nested NDJSON logs, parse the nested fields (like Windows Event Log keys under `System`, `EventData`, and `RenderingInfo`), map them to the normalized schema, and output them as NDJSON so that I can analyze Windows Event Logs in a unified format.

**Why this priority**: Core ingestion requirement. Delivers immediate value by parsing structured Windows Event JSON logs.

**Independent Test**: Can be tested by running the server, sending a single-line minified JSON string of `samples/json/sample-1.json` via TCP to port 5044, and verifying the mapped NDJSON output matches the expected format.

**Acceptance Scenarios**:

1. **Given** the TCP server is running, **When** an NDJSON line containing Windows Event data (e.g. `sample-1.json`) is sent over TCP, **Then** the server outputs a single-line NDJSON record to stdout matching the target schema.

---

### User Story 3 - Gracefully Handle Malformed Data (Priority: P2)

As an Operator, I want the server to isolate malformed inputs (invalid JSON, truncated syslog, etc.) to a dead-letter log or error sink and keep running, so that a single bad client doesn't crash the service or disrupt other connections.

**Why this priority**: Required by the project constitution for error isolation and resilience under load.

**Independent Test**: Can be tested by sending random binary noise or invalid JSON lines to the TCP listener and verifying that the server remains active and handles subsequent valid lines correctly.

**Acceptance Scenarios**:

1. **Given** the server is active, **When** an invalid JSON string (e.g., `{"invalid_json:`) is sent over TCP, **Then** the server writes a warning log with a dead-letter representation and continues to accept and parse subsequent valid inputs.

---

### User Story 4 - Configure Ingestion via Command Line (Priority: P2)

As an Operator, I want to configure the listening TCP port and the output destination via command-line arguments so that I can easily deploy and manage the service in different environments.

**Why this priority**: Required for standard CLI/daemon interaction and ease of operations.

**Independent Test**: Can be tested by running the daemon with `--port 6000` and sending a message to port 6000 to verify ingestion.

**Acceptance Scenarios**:

1. **Given** the daemon is launched with argument `--port 6000`, **When** a connection is opened on port 6000, **Then** the server successfully listens and processes the input data.

---

### Edge Cases

- **Large Payload Flood**: What happens when a client sends a payload line larger than 64KB? (System must truncate the line, drop the connection, and log a warning).
- **Missing Year in Syslog**: How does the parser handle RFC 3164 timestamps that do not include the year field? (System must assume the current UTC calendar year).
- **Empty and Sentinel values**: How does the system handle fields containing `-` or SIDs containing `S-1-0-0`? (System must omit these fields from output).
- **Mixed Formats in Connection**: How does the server handle receiving a Syslog line followed by a JSON line on the same TCP connection? (Per-line format detection must handle each dynamically).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: TCP server MUST listen on a configurable TCP port (default: 5044).
- **FR-002**: System MUST automatically detect the format of each incoming log line (per-line basis: first non-whitespace character is `{` -> JSON/NDJSON, otherwise Syslog).
- **FR-003**: System MUST parse both RFC 3164 Syslog messages (with PRI, timestamp, hostname, message body) and CEF extensions when present.
- **FR-004**: System MUST parse nested JSON (Windows Event Logs) and extract fields from configured paths (`System`, `EventData`, `RenderingInfo`, `OpenWEC`).
- **FR-005**: System MUST map all extracted fields to the normalized schema defined in `SCHEMA.md`.
- **FR-006**: System MUST output normalized logs as NDJSON (single line per record) to stdout or a configurable output sink.
- **FR-007**: System MUST handle malformed input gracefully by logging/routing to a dead-letter target without crashing the server or terminating other connections.
- **FR-008**: System MUST enforce a maximum payload size limit of 64KB per log line, disconnecting clients that exceed this limit.
- **FR-009**: System MUST run parsing asynchronously, ensuring that CPU-heavy parsing operations or large payloads do not block the single-threaded event loop.
- **FR-010**: System MUST support client-auth TLS configuration on the TCP listener if TLS parameters are supplied via the command line.
- **FR-011**: System MUST support graceful shutdown upon receiving termination signals (`SIGINT`, `SIGTERM`), ensuring all active sockets are drained within a configurable grace period and resources/ports are released cleanly.
- **FR-012**: System MUST enforce a maximum limit of concurrent TCP connections (default: 100) to prevent socket exhaustion.
- **FR-013**: System MUST enforce a configurable connection read/write idle timeout (default: 30 seconds) on active socket channels.

### Key Entities

- **NormalizedLog**: Represents the final structured output record. Attributes: `@timestamp` (ISO 8601 UTC string), `event.type`, `event.category`, `event.outcome`, `source.ip`, `user.name`, `host.name`, `log.level`, `message`.
- **IngestionClient**: Represents a single client socket connection. Attributes: host IP, port, connection status, number of consecutive parsing failures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The service parses both syslog and JSON sample inputs, producing outputs that are structurally and semantic-wise identical to `expected/sample-output.ndjson`.
- **SC-002**: The service can process 5,000 log events per second under continuous load without memory leaks or runaway resource usage.
- **SC-003**: A single malformed payload does not crash the service, and subsequent valid events are processed successfully within 50ms of connection recovery.
- **SC-004**: Under concurrent load of 100 simultaneous TCP connections, parsing latency per log line remains under 5ms from packet receipt to output.

## Assumptions

- Ingested log streams are newline-delimited (`\n` or `\r\n`).
- Syslog dates without a specified year (default in RFC 3164) are assumed to belong to the current UTC calendar year.
- Syslog dates without timezone metadata are assumed to be in UTC.
- Obscure SIDs (such as `S-1-0-0`) and `-` values represent empty/null and are omitted from the target mappings.
- Volumetric network-level protection (e.g. rate-limiting, source IP blocking) will be handled by external firewall rules or load balancers, while the application enforces connection-level size limits.
- The mapping of Syslog/CEF severities to `log.level` follows this standardized matrix:
  * Syslog Severity 0-3 (Emergency, Alert, Critical, Error) / CEF 7-10 -> `error`
  * Syslog Severity 4 (Warning) / CEF 4-6 -> `warning`
  * Syslog Severity 5-6 (Notice, Informational) / CEF 1-3 -> `info`
  * Syslog Severity 7 (Debug) / CEF 0 -> `debug`
