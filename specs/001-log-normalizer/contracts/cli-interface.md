# Interface Contracts: Log Normalizer Service

This document defines the interface contracts for interacting with the Log Normalizer service.

## 1. CLI Command-Line Contract

The service is invoked as a Python script/executable and accepts the following arguments:

| Flag | Argument Type | Default Value | Description |
|---|---|---|---|
| `--port` | Integer | `5044` | The TCP port the server listens on. |
| `--output` | String | `-` | Output destination. Standard file path or `-` (directs to stdout). |

### Example Invocations
```bash
# Run server listening on port 5044, outputting to stdout
uv run src/main.py --port 5044 --output -

# Run server listening on port 6000, writing logs to a file
uv run src/main.py --port 6000 --output /var/log/normalized.log
```

---

## 2. Ingestion Protocol Contract (TCP Socket)

The service acts as a line-oriented server.

- **Transport**: TCP
- **Line delimiter**: `\n` or `\r\n` (carriage return and newline)
- **Log encoding**: UTF-8
- **Maximum line size**: 64KB (65,536 bytes). If a client sends a line exceeding this limit, the server immediately drops the connection and discards the buffer.

---

## 3. Output Log Contract (NDJSON)

Each normalized event is output as a single line of minified JSON (NDJSON) to the specified destination.

### JSON Field Matrix
- `@timestamp`: ISO 8601 UTC string (`YYYY-MM-DDTHH:MM:SS.mmmZ`).
- `event.type`: String (`start`, `allowed`, etc.).
- `event.category`: String (`authentication`, `network`, etc.).
- `event.outcome`: String (`success`, `failure`, etc.).
- `source.ip`: (Optional) Valid IPv4/IPv6 address.
- `user.name`: (Optional) Extracted username.
- `host.name`: (Optional) Extracted hostname.
- `log.level`: String (`error`, `warning`, `info`, `debug`).
- `message`: (Optional) Raw message payload or description.

*Note: Optional fields are excluded from the output JSON document if their value is null or omitted.*
