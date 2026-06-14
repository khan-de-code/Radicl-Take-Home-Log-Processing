# Implementation Plan: Log Normalizer Service

**Branch**: `001-log-normalizer` | **Date**: 2026-06-14 | **Spec**: [spec.md](file:///home/dbatz/projects/Backend-Engineering-Excercise/specs/001-log-normalizer/spec.md)

**Input**: Feature specification from `/specs/001-log-normalizer/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

The Log Normalizer Service is a database-less, highly concurrent TCP log ingestion daemon written in Python 3.12+. It listens on a configurable TCP port, detects and parses incoming logs (either RFC 3164 Syslog with CEF extensions, or minified Windows Event NDJSON), maps them to a strictly typed normalized schema, and writes them to stdout or a designated log file. Malformed records are isolated to a dead-letter log or stderr to prevent server crashes. 

The service conforms to strict Python quality constraints: `ruff` is configured with all non-conflicting rules and Google-style docstrings format, and `pyrefly` is enabled in its most aggressive static typing mode. The execution begins with an environmental bootstrap: configuring `uv` for package management, creating a `.gitignore`, and defining a `justfile` for automated testing, linting, and formatting checks.

## Technical Context

**Language/Version**: Python 3.12+ (managed via `uv`)

**Primary Dependencies**: `pydantic` (for static schema typing and validation), `rich-click` (CLI framework), `pytest` (test suite)

**Storage**: None (stdout or local file sink only)

**Testing**: `pytest` (unit tests for parsers, integration tests for connection lifecycles, and golden-file comparison checks)

**Target Platform**: Linux server

**Project Type**: CLI daemon / TCP service

**Performance Goals**: 5,000 log events/second throughput; parsing latency < 5ms under load

**Constraints**: Max 64KB per log line; max 100 concurrent TCP connections; 30 seconds connection idle timeout

**Scale/Scope**: Ingestion server processing high-velocity security streams

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Type Safety [Pass]**: Standard Pydantic v2 models will be used to enforce SCHEMA.md types. No raw dict operations for the final output. Static validation will run under the most aggressive `pyrefly` configuration. (Constitution §I)
- **Error Isolation [Pass]**: Connection/parsing failures are isolated to a dead-letter queue or error destination. Single malformed log lines will not crash the server. (Constitution §II)
- **Testing & Quality [Pass]**: Strict unit, integration, and golden-file tests will run automatically via `pytest` before commits. (Constitution §III)
- **CLI/Logs Interface [Pass]**: Port, output paths, and parameters are configurable via standard CLI rich-click. Logs are sent to stderr. (Constitution §IV)
- **Resource Bounding & Async [Pass]**: Input lines are capped at 64KB, connections capped at 100, idle timeouts enforced at 30s, and CPU parsing is processed asynchronously without blocking the main event loop. (Constitution §V)

## Project Structure

### Documentation (this feature)

```text
specs/001-log-normalizer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Requirements quality checklist
└── contracts/           # Phase 1 output
    └── cli-interface.md # CLI command and NDJSON output contract
```

### Source Code (repository root)

```text
src/
├── domain/               # Core business logic (pure, framework-independent)
│   ├── __init__.py
│   ├── models.py         # NormalizedLog schema models (Pydantic)
│   ├── parser.py         # Syslog, CEF, and NDJSON format detection and parsing logic
│   ├── ports.py          # Interfaces defining inbound/outbound communication channels
│   └── utils.py          # Business utility logic (timezone/date adjustments)
├── adapters/             # Adapters implementing port interfaces
│   ├── __init__.py
│   ├── inbound/          # Driving adapters (TCP, CLI)
│   │   ├── __init__.py
│   │   ├── tcp_server.py # Asyncio TCP server listener adapter
│   │   └── cli.py        # Rich-click CLI command parser adapter
│   └── outbound/         # Driven adapters (Stdout, File Sinks)
│       ├── __init__.py
│       ├── stdout_sink.py # Standard output console adapter
│       └── file_sink.py  # Local filesystem writer adapter
├── __init__.py
└── main.py               # Dependency injection wireframe & service assembler

tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── test_parser.py   # Table-driven parser unit tests
│   └── test_models.py   # Type validation and mapping tests
├── integration/
│   └── test_server.py   # TCP connection lifecycle, timeouts, limits
└── golden/
    └── test_golden.py   # Snapshot validation against samples/expected outputs

justfile                 # Command runner for development tasks
.gitignore               # Workspace file exclusions
.pre-commit-config.yaml  # Local quality gate configuration running check suite before commit
pyproject.toml           # Configuration for Python dependencies, ruff, pyrefly, and pytest
```

**Structure Decision**: Hexagonal Architecture layout mapped under `src/domain/` and `src/adapters/` matching Option 1 reorganized.

## Local Quality Gates & Setup Details

### 1. Pre-commit Setup (`.pre-commit-config.yaml`)
To enforce that no code is committed unless it is formatted, linted, type-safe, and passes tests, a local hook configuration will execute:
- `ruff check --fix` and `ruff format`
- `pyrefly check` in its most aggressive mode
- `pytest` for unit and integration checks

### 2. Testing Configuration (`pyproject.toml`)
We configure `pytest` options inside `pyproject.toml`:
- Include `pytest-asyncio` for non-blocking server tests.
- Include `pytest-cov` to track coverage metrics.

### 3. Structured Logging
The daemon will write structured logs to `stderr` formatted as single-line JSON or formatted log objects (using standard library extensions or `structlog`) to ensure errors, connections, and yields are easily parseable and descriptive.

## Complexity Tracking

*No constitution check violations or deviations identified.*
