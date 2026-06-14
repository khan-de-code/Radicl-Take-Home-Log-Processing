"""Normalizer for Windows Event raw parsed outputs."""

from datetime import UTC, datetime

from domain.models import NormalizedLog

EVENT_ID_AUTH_START = {4624, 4625, 4648}
EVENT_ID_AUTH_END = {4634, 4647}
EVENT_ID_PROCESS_START = 4688
EVENT_ID_PROCESS_END = 4689
EVENT_ID_HOST_INFO_MIN = 4720
EVENT_ID_HOST_INFO_MAX = 4767


def _clean_sentinel(value: str | None) -> str | None:
    """Treat '-', empty strings, and null SIDs (S-1-0-0) as null and omit/clean them."""
    if value is None:
        return None
    stripped = value.strip()
    if stripped in ("-", "", "S-1-0-0"):
        return None
    return stripped


def _parse_iso8601_to_utc(raw_timestamp: str) -> str:
    """Parse any valid ISO 8601 timestamp and normalize it to UTC."""
    try:
        t_str = raw_timestamp.strip()
        if "." in t_str:
            dot_idx = t_str.index(".")
            offset_idx = -1
            for idx in range(dot_idx + 1, len(t_str)):
                if t_str[idx] in ("+", "-", "Z"):
                    offset_idx = idx
                    break

            if offset_idx != -1:
                subseconds = t_str[dot_idx + 1 : offset_idx]
                truncated_subseconds = subseconds[:6]
                offset = t_str[offset_idx:]
                t_str = t_str[:dot_idx] + "." + truncated_subseconds + offset

        if t_str.endswith("Z"):
            t_str = t_str[:-1] + "+00:00"

        dt = datetime.fromisoformat(t_str)
        dt_utc = dt.astimezone(UTC)

        ms = dt_utc.microsecond // 1000
        return f"{dt_utc.strftime('%Y-%m-%dT%H:%M:%S')}.{ms:03d}Z"
    except (ValueError, TypeError):
        return raw_timestamp


def _map_json_event_metadata(event_id: int) -> tuple[str, str]:
    """Resolve event.type and event.category based on Windows EventID."""
    event_type = "info"
    event_category = "host"

    if event_id in EVENT_ID_AUTH_START:
        event_type = "start"
        event_category = "authentication"
    elif event_id in EVENT_ID_AUTH_END:
        event_type = "end"
        event_category = "authentication"
    elif event_id == EVENT_ID_PROCESS_START:
        event_type = "start"
        event_category = "process"
    elif event_id == EVENT_ID_PROCESS_END:
        event_type = "end"
        event_category = "process"
    elif EVENT_ID_HOST_INFO_MIN <= event_id <= EVENT_ID_HOST_INFO_MAX:
        event_type = "info"
        event_category = "host"

    return event_type, event_category


def _map_json_outcome(keywords: list[str]) -> str:
    """Resolve event.outcome from RenderingInfo.Keywords list."""
    if not keywords:
        return "unknown"

    keywords_lower = [keyword.lower() for keyword in keywords]
    if any("success" in keyword for keyword in keywords_lower):
        return "success"
    if any("failure" in keyword for keyword in keywords_lower):
        return "failure"
    return "unknown"


def normalize_windows_event(data: dict[str, any]) -> NormalizedLog | None:
    """Normalize raw Windows Event dictionary into standard NormalizedLog."""
    system = data.get("System", {})
    event_data = data.get("EventData", {})
    rendering_info = data.get("RenderingInfo", {})
    open_wec = data.get("OpenWEC", {})

    # Extract target values
    raw_timestamp = system.get("TimeCreated")
    if not raw_timestamp:
        return None

    # Standardize timestamp format to ISO 8601 UTC
    timestamp = _parse_iso8601_to_utc(raw_timestamp)

    raw_event_id = system.get("EventID", 0)
    try:
        event_id = int(raw_event_id)
    except (TypeError, ValueError):
        event_id = 0

    event_type, event_category = _map_json_event_metadata(event_id)

    keywords = rendering_info.get("Keywords", [])
    event_outcome = _map_json_outcome(keywords)

    # Source IP: Prefer EventData.IpAddress, then OpenWEC.IpAddress
    source_ip = event_data.get("IpAddress") or open_wec.get("IpAddress")

    # User Name: Prefer TargetUserName, then SubjectUserName
    user_name = event_data.get("TargetUserName") or event_data.get("SubjectUserName")

    host_name = system.get("Computer")

    # Log Level
    level_raw = rendering_info.get("Level", "Information")
    log_level = "info"
    level_lower = level_raw.lower()
    if "info" in level_lower:
        log_level = "info"
    elif "warning" in level_lower:
        log_level = "warning"
    elif "error" in level_lower or "critical" in level_lower:
        log_level = "error"

    message = rendering_info.get("Message")

    return NormalizedLog(
        timestamp=timestamp,
        event_type=event_type,
        event_category=event_category,
        event_outcome=event_outcome,
        log_level=log_level,
        source_ip=_clean_sentinel(source_ip),
        user_name=_clean_sentinel(user_name),
        host_name=_clean_sentinel(host_name),
        message=_clean_sentinel(message),
    )
