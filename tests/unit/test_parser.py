"""Unit tests for domain log parser logic."""

from datetime import UTC, datetime

import pytest

from domain.models import NormalizedLog
from domain.parser import parse_line


def test_parse_line_empty() -> None:
    """Verify that empty/whitespace lines return None."""
    assert parse_line("") is None
    assert parse_line("   ") is None


@pytest.mark.parametrize(
    (
        "raw_line",
        "expected_timestamp",
        "expected_type",
        "expected_category",
        "expected_outcome",
        "expected_source_ip",
        "expected_user_name",
        "expected_host_name",
        "expected_log_level",
        "expected_msg",
    ),
    [
        # Sample 1: CEF event with EventID 4624 (logon success)
        (
            "<134>Dec 05 10:30:45 192.168.1.1 CEF:0|Microsoft|Windows|10.0|4624|An "
            "account was successfully logged on|1|src=10.0.50.42 suser=jsmith msg=An "
            "account was successfully logged on act=allow outcome=success",
            "2025-12-05T10:30:45.000Z",
            "start",
            "authentication",
            "success",
            "10.0.50.42",
            "jsmith",
            "192.168.1.1",
            "info",
            "An account was successfully logged on",
        ),
        # Sample 2: CEF event with EventID 4625 (logon failure)
        (
            "<133>Dec 05 10:35:22 192.168.1.1 CEF:0|Microsoft|Windows|10.0|4625|An "
            "account failed to log on|3|src=10.99.0.55 suser=admin msg=An account "
            "failed to log on act=denied outcome=failure",
            "2025-12-05T10:35:22.000Z",
            "start",
            "authentication",
            "failure",
            "10.99.0.55",
            "admin",
            "192.168.1.1",
            "info",
            "An account failed to log on",
        ),
        # Sample 3: CEF traffic event with act=allow
        (
            "<134>Dec 05 10:40:15 192.168.1.1 CEF:0|Palo Alto Networks|PAN-OS|11.0.0|TRAFFIC|"
            "traffic allow|1|src=192.168.1.100 dst=203.0.113.50 suser=jdoe act=allow "
            "proto=tcp spt=54321 dpt=443 msg=Connection allowed",
            "2025-12-05T10:40:15.000Z",
            "allowed",
            "network",
            "success",
            "192.168.1.100",
            "jdoe",
            "192.168.1.1",
            "info",
            "Connection allowed",
        ),
    ],
)
def test_parse_syslog_cef_valid(  # noqa: PLR0913
    raw_line: str,
    expected_timestamp: str,
    expected_type: str,
    expected_category: str,
    expected_outcome: str,
    expected_source_ip: str | None,
    expected_user_name: str | None,
    expected_host_name: str | None,
    expected_log_level: str | None,
    expected_msg: str,
) -> None:
    """Verify parsing of valid RFC 3164 Syslog logs with CEF extensions."""
    result = parse_line(raw_line)
    assert result is not None
    assert isinstance(result, NormalizedLog)
    assert result.timestamp == expected_timestamp
    assert result.event_type == expected_type
    assert result.event_category == expected_category
    assert result.event_outcome == expected_outcome
    assert result.source_ip == expected_source_ip
    assert result.user_name == expected_user_name
    assert result.host_name == expected_host_name
    assert result.log_level == expected_log_level
    assert result.message == expected_msg


def test_parse_syslog_timestamp_missing_year() -> None:
    """Verify that syslog timestamps without a year default to the current calendar year.

    But if the resolved date is > 7 days in the future, it defaults to the previous year.
    """
    current_year = datetime.now(UTC).year
    # Test case 1: Jan 01 (which is in the past compared to mid-2026/current date)
    # It should resolve to current_year.
    log_past = "<13>Jan 01 00:00:00 myhost CEF:0|Vendor|Prod|1.0|SIG|Name|3|msg=Test"
    res_past = parse_line(log_past)
    assert res_past is not None
    assert res_past.timestamp.startswith(f"{current_year}-01-01T00:00:00")

    # Test case 2: Dec 31 (which is in the future relative to 2026-06-13)
    # Since Dec 31 is > 7 days ahead of mid-June 2026, it should resolve to (current_year - 1).
    log_future = "<13>Dec 31 23:59:59 myhost CEF:0|Vendor|Prod|1.0|SIG|Name|3|msg=Test"
    res_future = parse_line(log_future)
    assert res_future is not None
    assert res_future.timestamp.startswith(f"{current_year - 1}-12-31T23:59:59")


def test_parse_json_valid_auth_success() -> None:
    """Verify parsing of valid Windows Event 4624 (authentication success) NDJSON logs."""
    raw_json = (
        '{"System": {"EventID": 4624, '
        '"TimeCreated": "2026-02-14T14:22:10.8831200Z", '
        '"Computer": "dc01.contoso.local"}, '
        '"EventData": {"TargetUserName": "jsmith", "IpAddress": "10.0.50.42"}, '
        '"RenderingInfo": {"Message": "An account was successfully logged on.", '
        '"Level": "Information", "Keywords": ["Audit Success"]}}'
    )
    result = parse_line(raw_json)
    assert result is not None
    assert result.timestamp.startswith("2026-02-14T14:22:10")
    assert result.event_type == "start"
    assert result.event_category == "authentication"
    assert result.event_outcome == "success"
    assert result.source_ip == "10.0.50.42"
    assert result.user_name == "jsmith"
    assert result.host_name == "dc01.contoso.local"
    assert result.log_level == "info"
    assert result.message == "An account was successfully logged on."


def test_parse_json_empty_fields_omitted() -> None:
    """Verify that "-" or empty values for TargetUserName or IpAddress are omitted.

    They must be mapped to None.
    """
    raw_json = (
        '{"System": {"EventID": 4624, '
        '"TimeCreated": "2026-02-14T14:22:10.8831200Z", '
        '"Computer": "dc01.contoso.local"}, '
        '"EventData": {"TargetUserName": "-", "IpAddress": ""}, '
        '"RenderingInfo": {"Message": "Logged on", '
        '"Level": "Information", "Keywords": ["Audit Success"]}}'
    )
    result = parse_line(raw_json)
    assert result is not None
    assert result.source_ip is None
    assert result.user_name is None


def test_parser_adjustments() -> None:
    """Verify leap-year, string EventID coercion, time offset, and sentinel cleaning."""
    # 1. String EventID coercion & timezone offset conversion to UTC Z
    raw_json_offset = (
        '{"System": {"EventID": "4624", '
        '"TimeCreated": "2026-02-14T14:22:10.883-05:00", '
        '"Computer": "-"}, '
        '"EventData": {"TargetUserName": "jsmith"}, '
        '"RenderingInfo": {"Message": "", '
        '"Level": "Information", "Keywords": ["Audit Success"]}}'
    )
    result = parse_line(raw_json_offset)
    assert result is not None
    # 14:22:10.883-05:00 converts to 19:22:10.883Z in UTC
    assert result.timestamp == "2026-02-14T19:22:10.883Z"
    assert result.event_type == "start"
    assert result.event_category == "authentication"

    # Sentinel cleaning of host_name and message
    assert result.host_name is None
    assert result.message is None

    # 2. Leap-year Feb 29 rollover validation
    # We test that adjust_syslog_year handles Feb 29.
    # When parsing syslog logs lacking year with "Feb 29", it should roll
    # over to a leap year (e.g. 2024 if current is 2026).
    # Let's verify it parses without raising an exception.
    log_leap = "<13>Feb 29 12:00:00 myhost CEF:0|Vendor|Prod|1.0|SIG|Name|3|msg=LeapYearTest"
    res_leap = parse_line(log_leap)
    assert res_leap is not None
    # Verify it parsed the timestamp successfully
    assert res_leap.timestamp.endswith("T12:00:00.000Z")
    # Year must be a leap year (e.g. 2024 or 2028 depending on system clock).
    year_part = int(res_leap.timestamp.split("-")[0])
    # Year must be leap year (divisible by 4)
    assert year_part % 4 == 0

    # 3. Optional fields sentinel cleaning in syslog cef normalizer
    log_sentinel_syslog = "<13>Jan 01 00:00:00 - CEF:0|Vendor|Prod|1.0|SIG|Name|3|msg=-"
    res_sentinel_syslog = parse_line(log_sentinel_syslog)
    assert res_sentinel_syslog is not None
    assert res_sentinel_syslog.host_name is None
    assert res_sentinel_syslog.message is None

    # 4. Null SID S-1-0-0 sentinel cleaning
    raw_json_sid = (
        '{"System": {"EventID": "4624", '
        '"TimeCreated": "2026-02-14T14:22:10.883-05:00", '
        '"Computer": "dc01.local"}, '
        '"EventData": {"TargetUserName": "S-1-0-0"}, '
        '"RenderingInfo": {"Message": "Msg", '
        '"Level": "Information", "Keywords": []}}'
    )
    res_json_sid = parse_line(raw_json_sid)
    assert res_json_sid is not None
    assert res_json_sid.user_name is None

    # 5. Syslog auth logoff context mapping
    log_logoff = "<13>Jan 01 00:00:00 myhost CEF:0|Vendor|Prod|1.0|SIG|Name|3|msg=User logged out"
    res_logoff = parse_line(log_logoff)
    assert res_logoff is not None
    assert res_logoff.event_type == "end"
    assert res_logoff.event_category == "authentication"
