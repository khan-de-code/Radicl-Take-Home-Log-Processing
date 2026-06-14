# Quickstart Validation Guide: Log Normalizer Service

This guide provides step-by-step instructions to validate the Log Normalizer service end-to-end.

## Prerequisites

- **Python**: v3.12+
- **uv**: v0.11.15+
- **just**: Command runner tool
- **netcat** (`nc`): Command-line tool for sending data over TCP sockets

---

## 1. Setup & Environment Verification

Verify dependencies and tool status:
```bash
# Verify uv installation
uv --version

# Install dependencies and sync virtualenv
just bootstrap  # Configured in justfile to run 'uv sync'
```

---

## 2. Validation Scenarios

### Scenario A: Start Ingestion Daemon
Run the server listening on a custom port and printing to stdout:
```bash
# Start daemon
just run --port 5044 --output -
```

### Scenario B: Ingest RFC 3164 Syslog Logs
While the daemon is running, open a new terminal and send syslog sample data:
```bash
# Send standard RFC 3164 CEF Syslog
nc localhost 5044 < samples/syslog/sample-1.log
```
**Expected Output (on daemon terminal stdout)**:
```json
{"@timestamp":"2025-12-05T10:30:45.000Z","event.type":"start","event.category":"authentication","event.outcome":"success","source.ip":"10.0.50.42","user.name":"jsmith","host.name":"192.168.1.1","log.level":"info","message":"An account was successfully logged on"}
```

### Scenario C: Ingest Windows NDJSON Logs
Send Windows Event Log in NDJSON format:
```bash
# Send JSON log
nc localhost 5044 < samples/json/sample-1.json
```
**Expected Output (on daemon terminal stdout)**:
Unified single-line NDJSON format representing the normalized Windows event attributes.

### Scenario D: Resource Limits & Resilience
Send a payload larger than 64KB:
```bash
# Generate a line with 70,000 characters and send it
python3 -c "print('A' * 70000)" | nc localhost 5044
```
**Expected Outcome**:
The server disconnects the client instantly, logs a warning to `stderr`, and remains running to accept subsequent connections.
