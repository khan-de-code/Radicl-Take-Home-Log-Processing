"""Golden file snapshot validation tests."""

import json
from pathlib import Path

from domain.parser import parse_line


def test_windows_json_golden_output() -> None:
    """Verify that parsed Windows Event JSON matches the expected golden output."""
    project_root = Path(__file__).parent.parent.parent

    # Load expected output records
    expected_path = project_root / "expected" / "sample-output.ndjson"
    with expected_path.open("r", encoding="utf-8") as f:
        expected_records = [json.loads(line) for line in f if line.strip()]

    # Load and parse json sample 1
    sample_1_path = project_root / "samples" / "json" / "sample-1.json"
    with sample_1_path.open("r", encoding="utf-8") as f:
        sample_1_data = json.load(f)
    # Minify to one line
    line_1 = json.dumps(sample_1_data)
    parsed_1 = parse_line(line_1)
    assert parsed_1 is not None

    # Load and parse json sample 2
    sample_2_path = project_root / "samples" / "json" / "sample-2.json"
    with sample_2_path.open("r", encoding="utf-8") as f:
        sample_2_data = json.load(f)
    line_2 = json.dumps(sample_2_data)
    parsed_2 = parse_line(line_2)
    assert parsed_2 is not None

    # Compare fields with expected golden logs
    # Sample 1 (Logon Success)
    assert parsed_1.timestamp == expected_records[0]["@timestamp"]
    assert parsed_1.event_type == expected_records[0]["event.type"]
    assert parsed_1.event_category == expected_records[0]["event.category"]
    assert parsed_1.event_outcome == expected_records[0]["event.outcome"]
    assert parsed_1.source_ip == expected_records[0]["source.ip"]
    assert parsed_1.user_name == expected_records[0]["user.name"]
    assert parsed_1.host_name == expected_records[0]["host.name"]
    assert parsed_1.log_level == expected_records[0]["log.level"]
    assert parsed_1.message == expected_records[0]["message"]

    # Sample 2 (Logon Failure)
    assert parsed_2.timestamp == expected_records[1]["@timestamp"]
    assert parsed_2.event_type == expected_records[1]["event.type"]
    assert parsed_2.event_category == expected_records[1]["event.category"]
    assert parsed_2.event_outcome == expected_records[1]["event.outcome"]
    assert parsed_2.source_ip == expected_records[1]["source.ip"]
    assert parsed_2.user_name == expected_records[1]["user.name"]
    assert parsed_2.host_name == expected_records[1]["host.name"]
    assert parsed_2.log_level == expected_records[1]["log.level"]
    assert parsed_2.message == expected_records[1]["message"]
