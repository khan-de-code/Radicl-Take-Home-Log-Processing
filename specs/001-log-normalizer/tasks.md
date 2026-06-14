# Tasks: Log Normalizer Service

**Input**: Design documents from `/specs/001-log-normalizer/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Initialize uv workspace and virtualenv in root pyproject.toml
- [X] T002 Configure git exclusions in .gitignore
- [X] T003 [P] Add rich-click to dependencies via uv and configure ruff (all non-conflicting rules, Google docstrings) and pyrefly strict type checks in pyproject.toml
- [X] T004 [P] Configure pytest, pytest-asyncio, and pytest-cov in pyproject.toml
- [X] T005 Create local check commands and bootstrap command in justfile
- [X] T006 Configure local pre-commit checks running ruff, pyrefly, and pytest in .pre-commit-config.yaml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Configure structured log formatter outputting to stderr in src/domain/utils.py
- [X] T008 [P] Create initial Pydantic schema validation structures in src/domain/models.py
- [X] T009 [P] Define core Ports for ingestion and outputs in src/domain/ports.py
- [X] T010 Implement basic asyncio TCP server bootstrap and shutdown loop in src/adapters/inbound/tcp_server.py and src/main.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Process RFC 3164 Syslog Logs (Priority: P1) 🎯 MVP

**Goal**: TCP listener ingests, parses, maps RFC 3164 Syslog logs to schema, and writes NDJSON to output.

**Independent Test**: Start daemon on port 5044, send `samples/syslog/sample-1.log` via netcat, and verify stdout matches the normalized JSON schema representation.

### Tests for User Story 1
- [X] T011 [P] [US1] Create table-driven unit tests for Syslog parsing (PRI, Header, CEF message) in tests/unit/test_parser.py
- [X] T012 [US1] Create integration test for TCP ingestion of RFC 3164 Syslog logs in tests/integration/test_server.py

### Implementation for User Story 1
- [X] T013 [P] [US1] Implement Syslog PRI extraction and facility/severity resolver in src/domain/parser.py
- [X] T014 [P] [US1] Implement CEF Extension message scanner/parser in src/domain/parser.py
- [X] T015 [US1] Map parsed Syslog/CEF fields to NormalizedLog models in src/domain/parser.py
- [X] T016 [US1] Integrate Syslog parser into the TCP reader stream processing coroutine in src/adapters/inbound/tcp_server.py
- [X] T017 [US1] Implement console output writer in src/adapters/outbound/stdout_sink.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Process NDJSON Logs (Priority: P1)

**Goal**: Ingest, format-detect, parse nested Windows JSON keys, map to schema, and write to output.

**Independent Test**: Send minified `samples/json/sample-1.json` via netcat to port 5044, and verify output matches target NDJSON.

### Tests for User Story 2
- [X] T018 [P] [US2] Create unit tests for format detection (Syslog vs JSON) and nested Windows JSON extraction paths in tests/unit/test_parser.py
- [X] T019 [US2] Create integration test for TCP ingestion of NDJSON logs in tests/integration/test_server.py

### Implementation for User Story 2
- [X] T020 [US2] Implement first-character inspection format detector in src/domain/parser.py
- [X] T021 [P] [US2] Implement nested field path extraction for Windows Event Logs in src/domain/parser.py
- [X] T022 [US2] Map extracted Windows JSON fields to NormalizedLog attributes in src/domain/parser.py
- [X] T023 [US2] Integrate JSON parser routing in the TCP reader stream handler in src/adapters/inbound/tcp_server.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently.

---

## Phase 5: User Story 3 - Gracefully Handle Malformed Data (Priority: P2)

**Goal**: Isolate parsing exceptions and invalid lines to prevent client drops or server crashes.

**Independent Test**: Stream binary noise and malformed lines to port 5044 and verify the daemon stays active and processes subsequent valid logs.

### Tests for User Story 3
- [X] T024 [P] [US3] Create unit tests for parser exception handling and fallback mapping in tests/unit/test_parser.py
- [X] T025 [US3] Create integration test sending invalid lines to server and checking error logs in tests/integration/test_server.py

### Implementation for User Story 3
- [X] T026 [US3] Implement line-oriented try-except blocks to catch parser errors in src/adapters/inbound/tcp_server.py
- [X] T027 [US3] Add dead-letter routing to log malformed events without interrupting the stream in src/adapters/inbound/tcp_server.py

**Checkpoint**: Daemon remains fully resilient to malformed payloads.

---

## Phase 6: User Story 4 - Configure Ingestion via Command Line & Optional TLS (Priority: P2)

**Goal**: Configure listening port and target output destination via rich-click CLI arguments, and support optional client-auth TLS configuration.

**Independent Test**: Launch daemon with `--port 6000 --output /tmp/norm.log`, verify beautiful help outputs, verify port binding, and confirm normalized output is written to `/tmp/norm.log`. Verify client-auth TLS rejects unauthenticated connections when cert parameters are provided.

### Tests for User Story 4
- [X] T028 [P] [US4] Create unit tests for rich-click CLI processing in tests/unit/test_cli.py
- [X] T029 [P] [US4] Create unit/integration tests for TLS connectivity and client-auth validation in tests/integration/test_server.py

### Implementation for User Story 4
- [X] T030 [US4] Implement CLI parser using rich-click in src/adapters/inbound/cli.py
- [X] T031 [US4] Wire CLI configurations (`port`, `output`) to bootstrap server and output adapter in src/main.py
- [X] T032 [US4] Implement SSL/TLS context loader and client-certificate verification in src/adapters/inbound/tcp_server.py
- [X] T033 [US4] Bind SSL context to the asyncio TCP listener if CLI certificate parameters are supplied in src/main.py
- [X] T034 [US4] Implement filesystem output sink in src/adapters/outbound/file_sink.py

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Resource limits, performance benchmarking, golden testing, and quality checks.

- [X] T035 Implement 64KB log line cap validation and client disconnection in src/adapters/inbound/tcp_server.py
- [X] T036 Implement connection concurrency limiting (max 100) and idle timeout (30 seconds) in src/adapters/inbound/tcp_server.py
- [ ] T037 Create golden-file snapshot tests against expected output directories in tests/golden/test_golden.py
- [ ] T038 Implement throughput and latency benchmarking scripts in tests/performance/benchmark.py
- [ ] T039 Run benchmarks locally to verify 5,000 events/second and < 5ms processing latency targets
- [ ] T040 [P] Run quickstart.md validation guide scenarios locally to confirm end-to-end functionality
- [ ] T041 [P] Verify code compliance against the pre-commit suite (format, lint, type checks, and pytest)

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) - blocks all user stories.
- **User Stories (Phases 3-6)**: Depend on Foundational completion.
- **Polish (Phase 7)**: Depends on all user stories being complete.

### Parallel Opportunities
- Setup tasks (T003, T004) can be worked on in parallel.
- Unit tests and parser logic (e.g. T013, T014) can be developed in parallel.
- Once Foundation (Phase 2) is finished, developers can build US1 (Syslog) and US2 (JSON parsing) features concurrently.

---

## Implementation Strategy
1. **MVP Scope**: User Story 1 (Ingest RFC 3164 Syslog logs). Stop and validate before adding NDJSON logs support.
2. **Incremental Delivery**: Setup → Foundation → US1 (MVP) → US2 (Windows NDJSON) → US3 (Graceful Error isolation) → US4 (CLI configs & TLS) → Polish (Limits, Benchmarks, and Golden tests).
