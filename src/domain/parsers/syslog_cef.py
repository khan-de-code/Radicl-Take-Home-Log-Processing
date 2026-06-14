"""Low-level parser strategy for RFC 3164 Syslog and CEF logs."""

import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger("log_normalizer")

CEF_HEADER_SPLIT_THRESHOLD = 7
CEF_MINIMUM_HEADERS = 8
SYSLOG_MINIMUM_TIMESTAMP_LENGTH = 15
SYSLOG_TIMESTAMP_WIDTH = 15


def parse_syslog_timestamp(timestamp_string: str) -> str:
    """Parse syslog timestamp and normalize it to ISO 8601 UTC with calendar year logic."""
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
    """Parse CEF extension key-value pairs using a single-pass character scanner."""
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


def _split_cef_headers(body: str) -> list[str]:
    """Split CEF payload body into individual header sections using a linear scan."""
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


def parse_syslog_cef_raw(line: str) -> dict[str, any] | None:
    """Parse raw RFC 3164 Syslog fields and CEF parts.

    Returns:
        A dict of raw extracted values or None if invalid syslog.
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

    result = {
        "syslog_severity": syslog_severity,
        "timestamp": timestamp,
        "host_name": host_name,
        "body": body,
        "is_cef": False,
    }

    if body.startswith("CEF:0"):
        header_parts = _split_cef_headers(body)
        if len(header_parts) >= CEF_MINIMUM_HEADERS:
            result.update(
                {
                    "is_cef": True,
                    "cef_device_vendor": header_parts[1],
                    "cef_device_product": header_parts[2],
                    "cef_device_version": header_parts[3],
                    "cef_device_event_class_id": header_parts[4],
                    "cef_name": header_parts[5],
                    "cef_severity": header_parts[6],
                    "cef_extension_string": header_parts[7],
                    "cef_extensions": parse_cef_extensions_linear(header_parts[7]),
                }
            )

    return result
