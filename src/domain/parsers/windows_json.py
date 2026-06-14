"""Low-level parser strategy for Windows Event NDJSON logs."""

import json
import logging

logger = logging.getLogger("log_normalizer")


def parse_windows_json_raw(line: str) -> dict[str, any] | None:
    """Parse raw nested Windows Event JSON fields.

    Returns:
        Extracted raw payload dict or None if invalid JSON.
    """
    try:
        return json.loads(line)
    except json.JSONDecodeError as decode_error:
        logger.warning("Failed to decode JSON log line: %s", decode_error)
        return None
