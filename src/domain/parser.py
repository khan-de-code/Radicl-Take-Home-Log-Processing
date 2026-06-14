"""Domain log parser entry point.

Routes incoming logs to the appropriate strategy by dispatching prefix keys
to modular parsers and normalizers.
"""

from collections.abc import Callable

from domain.models import NormalizedLog
from domain.normalizers.syslog_cef import normalize_syslog_cef
from domain.normalizers.windows_event import normalize_windows_event
from domain.parsers.syslog_cef import parse_syslog_cef_raw
from domain.parsers.windows_json import parse_windows_json_raw


def parse_syslog_cef_entry(line: str) -> NormalizedLog | None:
    """Wrapper that parses and normalizes Syslog CEF payloads."""
    raw = parse_syslog_cef_raw(line)
    if raw is not None:
        return normalize_syslog_cef(raw)
    return None


def parse_windows_json_entry(line: str) -> NormalizedLog | None:
    """Wrapper that parses and normalizes Windows JSON payloads."""
    raw = parse_windows_json_raw(line)
    if raw is not None:
        return normalize_windows_event(raw)
    return None


# Static dispatch registry mapping first non-whitespace character to appropriate entry function
PARSER_REGISTRY: dict[str, Callable[[str], NormalizedLog | None]] = {
    "{": parse_windows_json_entry,
    "<": parse_syslog_cef_entry,
}


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

    # Dynamic format dispatch using first character registry
    prefix = stripped[0]
    parser_func = PARSER_REGISTRY.get(prefix)
    if parser_func:
        return parser_func(stripped)

    return None
