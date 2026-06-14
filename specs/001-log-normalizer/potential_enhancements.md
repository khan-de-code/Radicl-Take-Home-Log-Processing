# Log Normalizer Service: Potential Enhancements

This document lists the architectural and scaling enhancements proposed to optimize processing performance and format extensibility:

---

### A. Non-blocking CPU Processing (Parser Offloading)
- **Concept**: Log parsing (regex, string manipulation, JSON traversal) is CPU-bound. Currently, the server processes lines synchronously in the main event thread:
  ```python
  normalized = self.parser(line)
  ```
- **Enhancement**: Offload CPU-bound parsing routines from the single-threaded event loop to worker threads or a process pool to ensure the server remains highly responsive under volumetric spikes:
  ```python
  normalized = await asyncio.to_thread(self.parser, line)
  ```

### B. Implement Pipeline Provider Pattern for Multi-Format Support
- **Concept**: The current format detector utilizes a hardcoded first-character inspection (`{` for JSON, `<` for Syslog). This cannot support new JSON-based formats (like AWS CloudTrail, GCP Logs, or Nginx JSON logs) because they will conflict on the `{` routing.
- **Enhancement**: Transition to a modular **Pipeline Provider Pattern** where format providers subclass a common interface:
  ```python
  class LogFormatProvider(Protocol):
      def can_parse(self, line: str) -> bool: ...
      def parse(self, line: str) -> NormalizedLog | None: ...
  ```
  Register providers in a prioritized list to sequentially evaluate each incoming line dynamically, separating parsing logic into clean, pluggable modules.

### C. Bulk Log Emitters & Buffered Sinks
- **Concept**: The daemon currently writes output records to `stdout` or file sinks individually per line, which incurs a high disk and system I/O overhead.
- **Enhancement**: Introduce an asynchronous memory queue/buffer in the output adapter that flushes logs in bulk batches (e.g., every 500 records or 100ms) to maximize performance.

### D. SSL/TLS Handshake Timeout (Slowloris SSL Protection)
- **Concept**: In TLS mode, Python's `asyncio.start_server` performs the TLS handshake before yielding control to our connection handler. A client can open a socket and never send handshake bytes, stalling the connection slot indefinitely and bypassing the `idle_timeout` check.
- **Enhancement**: Wrap connection acceptance with an asynchronous timeout wrapper to force-close connections that fail to complete the SSL handshake within a short window (e.g., 5 seconds).

### E. String Length Constraints (Pydantic Validation Protection)
- **Concept**: Although the TCP reader caps raw log lines at 64KB, individual fields inside the JSON or CEF payloads (like `user.name` or `host.name`) do not have length constraints. An attacker can send a valid 60KB payload containing a massive string for a single field, leading to bloated database records and higher serialization overhead.
- **Enhancement**: Update the Pydantic model (`NormalizedLog`) to enforce reasonable string length boundaries using `StringConstraints` (e.g., capping host and user names at 256 characters) to protect downstream buffers.
