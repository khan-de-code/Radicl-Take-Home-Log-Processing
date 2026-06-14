"""Normalizer for Windows Event raw parsed outputs."""

from domain.models import NormalizedLog

EVENT_ID_AUTH_START = {4624, 4625, 4648}
EVENT_ID_AUTH_END = {4634, 4647}
EVENT_ID_PROCESS_START = 4688
EVENT_ID_PROCESS_END = 4689
EVENT_ID_HOST_INFO_MIN = 4720
EVENT_ID_HOST_INFO_MAX = 4767


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
    if "." in raw_timestamp and raw_timestamp.endswith("Z"):
        parts = raw_timestamp.split(".")
        fraction = parts[1][:-1][:3]  # Take first 3 decimal digits
        timestamp = f"{parts[0]}.{fraction}Z"
    else:
        timestamp = raw_timestamp

    event_id = system.get("EventID", 0)
    event_type, event_category = _map_json_event_metadata(event_id)

    keywords = rendering_info.get("Keywords", [])
    event_outcome = _map_json_outcome(keywords)

    # Source IP: Prefer EventData.IpAddress, then OpenWEC.IpAddress
    source_ip = event_data.get("IpAddress") or open_wec.get("IpAddress")
    if source_ip in ["-", ""]:
        source_ip = None

    # User Name: Prefer TargetUserName, then SubjectUserName
    user_name = event_data.get("TargetUserName") or event_data.get("SubjectUserName")
    if user_name in ["-", ""]:
        user_name = None

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

    message = rendering_info.get("Message") or "Windows Event Log"

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
