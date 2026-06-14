"""Domain log parser entry point.

This module implements the primary parser logic that routes incoming logs to the
appropriate parser (Syslog CEF or Windows NDJSON) based on signature detection.
"""

import logging

from domain.models import NormalizedLog

logger = logging.getLogger("log_normalizer")


def parse_line(line: str) -> NormalizedLog | None:
    """Detect format of the log line and parse it into a NormalizedLog.

    Args:
        line: The raw unparsed log line.

    Returns:
        NormalizedLog if parsing succeeds, None if the line is ignored or skipped.
    """
    # NOTE: Implement full CEF and NDJSON parser detection.
    # This is currently a dummy implementation to allow bootstrap and verification.
    stripped = line.strip()
    if not stripped:
        return None

    # Dummy parsing: return a stub log to allow bootstrapping.
    return NormalizedLog(
        timestamp="2026-06-13T22:45:00Z",
        host="dummy-host",
        service="dummy-service",
        severity="INFO",
        event_name="dummy-event",
        payload={"raw": stripped},
    )
