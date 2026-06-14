"""Normalizer for RFC 3164 Syslog and CEF parsed outputs."""

from domain.models import NormalizedLog

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


def _resolve_by_event_class(class_id: str, action: str) -> tuple[str, str, str] | None:
    """Resolve mapping properties based on Device Event Class ID."""
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
    """Resolve mapping properties based on action keywords and message contents."""
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


def normalize_syslog_cef(raw_data: dict[str, any]) -> NormalizedLog:
    """Normalize raw Syslog/CEF field dictionary into standard NormalizedLog."""
    timestamp = raw_data["timestamp"]
    host_name = raw_data["host_name"]
    syslog_severity = raw_data["syslog_severity"]
    body = raw_data["body"]

    # Ingestion default mapping
    event_type = "info"
    event_category = "host"
    event_outcome = "unknown"
    log_level = SYSLOG_SEVERITY_MAP.get(syslog_severity, "info")
    source_ip = None
    user_name = None
    message = body

    if raw_data.get("is_cef"):
        class_id = raw_data["cef_device_event_class_id"]
        cef_name = raw_data["cef_name"]
        cef_severity_string = raw_data["cef_severity"]
        extensions = raw_data["cef_extensions"]

        if cef_severity_string in CEF_SEVERITY_MAP:
            log_level = CEF_SEVERITY_MAP[cef_severity_string]

        source_ip = extensions.get("src")
        user_name = extensions.get("suser")
        if user_name == "-":
            user_name = None
        if source_ip == "-":
            source_ip = None

        message = extensions.get("msg") or cef_name or body
        action = extensions.get("act", "")

        resolved = _resolve_by_event_class(class_id, action)
        if resolved:
            event_type, event_category, event_outcome = resolved
        else:
            event_type, event_category, event_outcome = _resolve_by_keyword_matching(
                message, action
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
