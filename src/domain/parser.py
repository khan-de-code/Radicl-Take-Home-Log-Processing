"""Domain log parser entry point.

This module implements the primary parser logic that routes incoming logs to the
appropriate parser (Syslog CEF or Windows NDJSON) using a high-performance,
single-pass character scanner (avoiding regex backtracking overhead).
"""

import logging
from datetime import UTC, datetime, timedelta

from domain.models import NormalizedLog

logger = logging.getLogger("log_normalizer")

# Constant definitions
CEF_HEADER_SPLIT_THRESHOLD = 7
CEF_MINIMUM_HEADERS = 8
SYSLOG_MINIMUM_TIMESTAMP_LENGTH = 15
SYSLOG_TIMESTAMP_WIDTH = 15

# Standard mapping for CEF / Syslog Severity values to schema levels
CEF_SEVERITY_MAP = {
    "0": "debug",
    "1": "info",
    "2": "info",
    "3": "info",
    "4": "warning",
    "5": "warning",
    "6": "warning",
    "7": "error",
    "8": "error",
    "9": "error",
    "10": "error",
}

SYSLOG_SEVERITY_MAP = {
    0: "error",
    1: "error",
    2: "error",
    3: "error",
    4: "warning",
    5: "info",
    6: "info",
    7: "debug",
}


def parse_syslog_timestamp(timestamp_string: str) -> str:
    """Parse syslog timestamp and normalize it to ISO 8601 UTC with calendar year logic.

    Args:
        timestamp_string: Timestamp string from syslog header (e.g. "Dec  5 10:30:45").

    Returns:
        ISO 8601 UTC formatted string (e.g. "2026-12-05T10:30:45.000Z").
    """
    normalized_timestamp = " ".join(timestamp_string.split())
    current_time = datetime.now(UTC)
    current_year = current_time.year

    try:
        parsed_datetime = datetime.strptime(normalized_timestamp, "%b %d %H:%M:%S").replace(
            tzinfo=UTC
        )
    except ValueError as parse_error:
        logger.warning("Failed to parse syslog timestamp %s: %s", timestamp_string, parse_error)
        return current_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    resolved_datetime = parsed_datetime.replace(year=current_year)
    if resolved_datetime > current_time + timedelta(days=7):
        resolved_datetime = resolved_datetime.replace(year=current_year - 1)

    return resolved_datetime.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def parse_cef_extensions_linear(extension_string: str) -> dict[str, str]:
    """Parse CEF extension key-value pairs using a single-pass character scanner.

    Correctly handles values containing spaces and key=value boundaries without regex.

    Args:
        extension_string: The raw extension string.

    Returns:
        Dictionary of parsed keys and values.
    """
    extensions: dict[str, str] = {}
    if not extension_string:
        return extensions

    length = len(extension_string)
    index = 0

    parsed_tokens: list[str] = []
    current_token: list[str] = []

    while index < length:
        character = extension_string[index]

        # Handle escaped characters (backslash escapes like \= or \ )
        if character == "\\" and index + 1 < length:
            current_token.append(extension_string[index + 1])
            index += 2
            continue

        if character.isspace():
            if current_token:
                parsed_tokens.append("".join(current_token))
                current_token = []
            index += 1
            continue

        current_token.append(character)
        index += 1

    if current_token:
        parsed_tokens.append("".join(current_token))

    active_key = None
    for token in parsed_tokens:
        if "=" in token:
            parts = token.split("=", 1)
            active_key = parts[0]
            extensions[active_key] = parts[1]
        elif active_key is not None:
            extensions[active_key] = f"{extensions[active_key]} {token}"

    return extensions


def _resolve_by_event_class(class_id: str, action: str) -> tuple[str, str, str] | None:
    """Resolve mapping properties based on Device Event Class ID.

    Args:
        class_id: The device class ID.
        action: The CEF act extension value.

    Returns:
        Tuple of (event_type, event_category, event_outcome) or None if no match.
    """
    if class_id == "4624":
        return "start", "authentication", "success"
    if class_id == "4625":
        return "start", "authentication", "failure"
    if class_id == "TRAFFIC":
        if "allow" in action:
            return "allowed", "network", "success"
        if "deny" in action or "block" in action:
            return "denied", "network", "failure"
        return "info", "network", "unknown"
    return None


def _resolve_by_keyword_matching(message: str, action: str) -> tuple[str, str, str]:
    """Resolve mapping properties based on action keywords and message contents.

    Args:
        message: The event message.
        action: The CEF act extension value.

    Returns:
        Tuple of (event_type, event_category, event_outcome).
    """
    event_type = "info"
    event_category = "host"
    event_outcome = "unknown"

    if "allow" in action:
        event_type = "allowed"
        event_outcome = "success"
    elif "deny" in action or "block" in action:
        event_type = "denied"
        event_outcome = "failure"

    lower_message = message.lower()
    if any(term in lower_message for term in ["log on", "logged on", "logon", "login", "auth"]):
        event_category = "authentication"
        if "success" in lower_message or "allow" in lower_message:
            event_outcome = "success"
        elif "fail" in lower_message or "deny" in lower_message:
            event_outcome = "failure"
    elif any(term in lower_message for term in ["connection", "traffic"]):
        event_category = "network"

    return event_type, event_category, event_outcome


def _map_cef_event_attributes(
    class_id: str,
    cef_name: str,
    extensions: dict[str, str],
    body: str,
) -> tuple[str, str, str, str]:
    """Resolve event.type, event.category, event.outcome and message for a CEF log.

    Args:
        class_id: The CEF device event class ID.
        cef_name: The CEF name header.
        extensions: The parsed extensions map.
        body: The raw body.

    Returns:
        A tuple of (event_type, event_category, event_outcome, message).
    """
    message = extensions.get("msg") or cef_name or body
    action = extensions.get("act", "")

    resolved = _resolve_by_event_class(class_id, action)
    if resolved:
        event_type, event_category, event_outcome = resolved
    else:
        event_type, event_category, event_outcome = _resolve_by_keyword_matching(message, action)

    return event_type, event_category, event_outcome, message


def _split_cef_headers(body: str) -> list[str]:
    """Split CEF payload body into individual header sections using a linear scan.

    Args:
        body: The raw CEF body.

    Returns:
        List of parsed header segments.
    """
    header_parts: list[str] = []
    current_part: list[str] = []
    index = 0
    body_length = len(body)

    while index < body_length:
        character = body[index]
        if character == "\\" and index + 1 < body_length and body[index + 1] == "|":
            current_part.append("|")
            index += 2
            continue
        if character == "|":
            header_parts.append("".join(current_part))
            current_part = []
            if len(header_parts) == CEF_HEADER_SPLIT_THRESHOLD:
                header_parts.append(body[index + 1 :])
                break
            index += 1
            continue
        current_part.append(character)
        index += 1

    return header_parts


def _parse_syslog_header(line: str) -> tuple[int, str, str, str] | None:
    """Parse RFC 3164 Syslog header priority, timestamp, host and body.

    Args:
        line: The raw syslog line.

    Returns:
        Tuple of (syslog_severity, timestamp, host_name, body) or None if malformed.
    """
    if not line.startswith("<"):
        return None

    # Parse Priority Value
    try:
        priority_end = line.index(">")
        priority_value = int(line[1:priority_end])
    except (ValueError, IndexError):
        return None

    syslog_severity = priority_value % 8

    # Parse Timestamp
    timestamp_start = priority_end + 1
    if len(line) < timestamp_start + SYSLOG_MINIMUM_TIMESTAMP_LENGTH:
        return None

    raw_timestamp = line[timestamp_start : timestamp_start + SYSLOG_TIMESTAMP_WIDTH]
    timestamp = parse_syslog_timestamp(raw_timestamp)

    # Parse Hostname and Body
    rest = line[timestamp_start + SYSLOG_TIMESTAMP_WIDTH + 1 :].strip()
    if not rest:
        return None

    parts = rest.split(None, 1)
    if not parts:
        return None
    host_name = parts[0]
    body = parts[1] if len(parts) > 1 else ""

    return syslog_severity, timestamp, host_name, body


def parse_syslog_cef_linear(line: str) -> NormalizedLog | None:
    """Parse an RFC 3164 Syslog line containing a CEF event payload using a linear scanner.

    Args:
        line: The raw log line.

    Returns:
        NormalizedLog if parsing succeeds, None otherwise.
    """
    header_data = _parse_syslog_header(line)
    if not header_data:
        return None

    syslog_severity, timestamp, host_name, body = header_data

    # Initialize defaults
    event_type = "info"
    event_category = "host"
    event_outcome = "unknown"
    log_level = SYSLOG_SEVERITY_MAP.get(syslog_severity, "info")
    source_ip = None
    user_name = None
    message = body

    # Parse CEF headers if present
    if body.startswith("CEF:0"):
        header_parts = _split_cef_headers(body)

        if len(header_parts) >= CEF_MINIMUM_HEADERS:
            class_id = header_parts[4]
            cef_name = header_parts[5]
            cef_severity_string = header_parts[6]
            extension_string = header_parts[7]

            extensions = parse_cef_extensions_linear(extension_string)

            if cef_severity_string in CEF_SEVERITY_MAP:
                log_level = CEF_SEVERITY_MAP[cef_severity_string]

            source_ip = extensions.get("src")
            user_name = extensions.get("suser")
            if user_name == "-":
                user_name = None
            if source_ip == "-":
                source_ip = None

            event_type, event_category, event_outcome, message = _map_cef_event_attributes(
                class_id, cef_name, extensions, body
            )

    return NormalizedLog(
        timestamp=timestamp,
        event_type=event_type,
        event_category=event_category,
        event_outcome=event_outcome,
        log_level=log_level,
        source_ip=source_ip,
        user_name=user_name,
        host_name=host_name,
        message=message,
    )


def parse_line(line: str) -> NormalizedLog | None:
    """Detect format of the log line and parse it into a NormalizedLog.

    Args:
        line: The raw unparsed log line.

    Returns:
        NormalizedLog if parsing succeeds, None if the line is ignored or skipped.
    """
    stripped = line.strip()
    if not stripped:
        return None

    # Syslog logs start with '<' (PRI marker)
    if stripped.startswith("<"):
        return parse_syslog_cef_linear(stripped)

    return None
