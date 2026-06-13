<!--
### Sync Impact Report
- Version change: 1.1.0 -> 1.2.0
- Modified principles:
  - Technical Stack & Implementation Constraints -> Add uv (v0.11.15+) as the mandatory environment/project manager
  - Development Workflow & Quality Gates -> Change test quality gate command to 'uv run pytest'
- Added sections: none
- Technical Stack: Python 3.12+, uv
- Templates requiring updates: none
- Follow-up TODOs: none
-->

# Log Normalizer Service Constitution

## Core Principles

### I. Code Quality & Strict Type Safety
Every incoming message MUST be parsed and mapped using type-safe structures (e.g., Python Pydantic models or typed Dataclasses with explicit JSON/field mapping). Raw dict operations for the final output schema are forbidden. All data mapping rules from SCHEMA.md must be statically typed, ensuring absolute adherence to required fields, correct ISO 8601 UTC formatting, and explicit handling of null or sentinel values (like `-` or `S-1-0-0`). Code must have zero linting errors (e.g., passing Ruff / Flake8 / MyPy) and zero magic constants.

### II. Dual-Format Parsing & Strict Error Isolation
The service MUST support parsing both RFC 3164 Syslog and Windows Event Log (NDJSON) formats. Format detection must be reliable (e.g., checking for leading `{` characters for JSON) and robust. A parsing failure on a single connection or record MUST NEVER crash the server or affect other connections. Malformed records must be handled gracefully: safely logged, and the server must continue processing.

### III. Comprehensive Testing & Golden-File Validation
A rigorous testing suite is mandatory. Every component (TCP listener, format detector, parsers, and schema mappers) must have unit tests, with table-driven tests covering positive and negative edge cases. Integration tests must validate the full TCP connection lifecycle. Finally, a golden-file/snapshot test suite must run mapper output against the expected outputs (e.g., expected/sample-output.ndjson) to guarantee exact matching of output fields and formats before commit.

### IV. Consistent User Experience & CLI/Log Interface
The user experience of this daemon is defined by its interaction interface. The TCP listener port, log sinks, and output destinations MUST be configurable via standard CLI arguments (e.g., argparse) with sensible defaults and environment variable overrides. Run-time feedback, startup indicators, and configuration summaries must be clearly printed. Application errors and connection summaries must be written to stderr as structured logs with uniform levels (info, warn, error).

### V. Resource Bounding & Performance Efficiency
The service must meet strict performance requirements to prevent resource exhaustion. Memory allocation on the hot path (packet/stream reading and parsing) must be minimized using buffered reading, memory-efficient generators, and bounded-size inputs. Connections must have explicit read/write timeouts and keep-alive limits to handle backpressure and network drops gracefully. CPU and memory benchmarks must be used to verify that parsing throughput scales linearly with load without runaway memory leakage.

## Technical Stack & Implementation Constraints
- **Language**: Python (v3.12+).
- **Environment & Project Manager**: `uv` (v0.11.15+). All dependencies and tool execution must be managed through `uv`.
- **Dependencies**: Minimize external libraries. Standard library modules (`socket`, `json`, `argparse`, `logging`) must be preferred. If third-party packages are needed (e.g., `pydantic` for validation, `pytest` for testing), they must be explicitly justified, vetted, and added via `uv add`.
- **Safety**: No unhandled exception leaks or thread/coroutine leaks. Contexts/timeouts must be propagated to all network operations for graceful cancellation.

## Development Workflow & Quality Gates
- **Git Flow**: All feature implementations must be done on dedicated branches. Commits must follow the Conventional Commits specification (e.g., `feat:`, `fix:`, `test:`).
- **Quality Gates**: No code can be committed without all tests passing (`uv run pytest`) and the linter/type checker running successfully with zero errors.
- **AI Usage**: Any AI-assisted code generation or design assistance must be documented in `AI_USAGE.md` as required by the coding exercise.

## Governance
This Constitution holds authority over all engineering and design decisions in this repository. Amendments to these principles require updating the version following semantic versioning principles and documenting the change in the Sync Impact Report at the top of this document. All code reviews and quality checks must enforce compliance with these principles.

**Version**: 1.2.0 | **Ratified**: 2026-06-13 | **Last Amended**: 2026-06-13
