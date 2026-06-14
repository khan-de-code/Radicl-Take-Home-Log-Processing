# Memory Synthesis

## Current Scope
- Feature: 001-log-normalizer
- Spec: Feature Specification: Log Normalizer Service
- Feature folder: specs/001-log-normalizer
- Spec context: # Feature Specification : Log Normalizer Service **Feature Branch **: `001-log-normalizer` **Created**: 2026-06-13 **Status**: Draft **Input**: User description : "Given the contents of README .md and SCHEMA .md, build an application that...

## Relevant Project Context
- [none]

## Relevant Decisions
- [D1] The service MUST support parsing both RFC 3164 Syslog and Windows Event Log (NDJSON) formats. Format detection must be reliable (e.g., checking for leading { characters for JSON) and robust. A parsing failure on a single connection or record MUST NEVER crash the server or affect other connections. (Source: `.specify/memory/constitution.md`)
- [D2] The service must meet strict performance requirements to prevent resource exhaustion. Memory allocation on the hot path (packet/stream reading and parsing) must be minimized using buffered reading, memory-efficient generators, and bounded-size inputs capped at a maximum of 64KB per log line. Connections must have explicit read/write timeouts and keep-alive limits to handle backpressure and network drops gracefully. (Source: `.specify/memory/constitution.md`)
- [D3] The user experience of this daemon is defined by its interaction interface. The TCP listener port, log sinks, and output destinations MUST be configurable via standard CLI arguments (e.g., argparse) with sensible defaults and environment variable overrides. Run-time feedback, startup indicators, and configuration summaries must be clearly printed. (Source: `.specify/memory/constitution.md`)
- [D4] A rigorous testing suite is mandatory. Every component (TCP listener, format detector, parsers, and schema mappers) must have unit tests, with table-driven tests covering positive and negative edge cases. Integration tests must validate the full TCP connection lifecycle. (Source: `.specify/memory/constitution.md`)
- [D5] Every incoming message MUST be parsed and mapped using type-safe structures (e.g., Python Pydantic models or typed Dataclasses with explicit JSON/field mapping). Raw dict operations for the final output schema are forbidden. All data mapping rules from SCHEMA.md must be statically typed, ensuring absolute adherence to required fields, correct ISO 8601 UTC formatting, and explicit handling of null or sentinel values (like - or S-1-0-0 ). (Source: `.specify/memory/constitution.md`)

## Active Architecture Constraints
- [none]

## Accepted Deviations
- [none]

## Relevant Security Constraints
- [none]

## Related Historical Lessons
- [none]

## Conflict Warnings
- [none]

## Retrieval Notes
- Index entries considered: 10
- Source sections read: 10
- Budget status: within limit
