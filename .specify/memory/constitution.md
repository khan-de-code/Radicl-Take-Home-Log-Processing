<!--
### Sync Impact Report
- Version change: [CONSTITUTION_VERSION] -> 1.0.0
- Modified principles:
  - [PRINCIPLE_1_NAME] -> I. Code Quality & Strict Type Safety
  - [PRINCIPLE_2_NAME] -> II. Dual-Format Parsing & Strict Error Isolation
  - [PRINCIPLE_3_NAME] -> III. Comprehensive Testing & Golden-File Validation
  - [PRINCIPLE_4_NAME] -> IV. Consistent User Experience & CLI/Log Interface
  - [PRINCIPLE_5_NAME] -> V. Resource Bounding & Performance Efficiency
- Added sections:
  - Technical Stack & Implementation Constraints
  - Development Workflow & Quality Gates
- Removed sections: none
- Templates requiring updates:
  - .specify/templates/plan-template.md (✅ updated)
  - .specify/templates/spec-template.md (✅ updated)
  - .specify/templates/tasks-template.md (✅ updated)
- Follow-up TODOs: none
-->

# Log Normalizer Service Constitution

## Core Principles

### I. Code Quality & Strict Type Safety
Every incoming message MUST be parsed and mapped using type-safe structures (e.g., Go structs with explicit JSON/field tags). Raw map operations (e.g. `map[string]any`) for the final output schema are forbidden. All data mapping rules from SCHEMA.md must be statically typed, ensuring absolute adherence to required fields, correct ISO 8601 UTC formatting, and explicit handling of null or sentinel values (like `-` or `S-1-0-0`). Code must have zero linting errors and zero magic constants.

### II. Dual-Format Parsing & Strict Error Isolation
The service MUST support parsing both RFC 3164 Syslog and Windows Event Log (NDJSON) formats. Format detection must be reliable (e.g., checking for leading `{` characters for JSON) and robust. A parsing failure on a single connection or record MUST NEVER crash the server or affect other connections. Malformed records must be handled gracefully: safely logged, and the server must continue processing.

### III. Comprehensive Testing & Golden-File Validation
A rigorous testing suite is mandatory. Every component (TCP listener, format detector, parsers, and schema mappers) must have unit tests, with table-driven tests covering positive and negative edge cases. Integration tests must validate the full TCP connection lifecycle. Finally, a golden-file/snapshot test suite must run mapper output against the expected outputs (e.g., expected/sample-output.ndjson) to guarantee exact matching of output fields and formats before commit.

### IV. Consistent User Experience & CLI/Log Interface
The user experience of this daemon is defined by its interaction interface. The TCP listener port, log sinks, and output destinations MUST be configurable via standard CLI flags (e.g., --port, --sink) with sensible defaults and environment variable overrides. Run-time feedback, startup indicators, and configuration summaries must be clearly printed. Application errors and connection summaries must be written to stderr as structured logs with uniform levels (info, warn, error).

### V. Resource Bounding & Performance Efficiency
The service must meet strict performance requirements to prevent resource exhaustion. Memory allocation on the hot path (packet/stream reading and parsing) must be minimized using buffer pooling (e.g., sync.Pool) and bounded-size readers. Connections must have explicit read/write deadlines and keep-alive limits to handle backpressure and network drops gracefully. CPU and memory benchmarks must be used to verify that parsing throughput scales linearly with load without runaway memory leakage.

## Technical Stack & Implementation Constraints
- **Language**: Go (v1.22+).
- **Dependencies**: Minimize external libraries. Standard library packages (`net`, `encoding/json`, `flag`, `log/slog`) must be preferred. If third-party packages are needed for syslog parsing or advanced CLI, they must be explicitly justified and vetted.
- **Safety**: No `unsafe` packages or unhandled goroutine leaks. Contexts (`requestContext`) must be propagated to all network operations for graceful cancellation.

## Development Workflow & Quality Gates
- **Git Flow**: All feature implementations must be done on dedicated branches. Commits must follow the Conventional Commits specification (e.g., `feat:`, `fix:`, `test:`).
- **Quality Gates**: No code can be committed without all tests passing (`go test -v ./...`) and the linter running successfully with zero errors.
- **AI Usage**: Any AI-assisted code generation or design assistance must be documented in `AI_USAGE.md` as required by the coding exercise.

## Governance
This Constitution holds authority over all engineering and design decisions in this repository. Amendments to these principles require updating the version following semantic versioning principles and documenting the change in the Sync Impact Report at the top of this document. All code reviews and quality checks must enforce compliance with these principles.

**Version**: 1.0.0 | **Ratified**: 2026-06-13 | **Last Amended**: 2026-06-13
