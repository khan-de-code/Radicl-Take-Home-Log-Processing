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
