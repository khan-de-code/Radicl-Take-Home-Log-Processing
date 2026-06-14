Feature: Log normalizer daemon TCP ingestion

  Scenario: Ingest and parse a valid RFC 3164 Syslog CEF message over TCP
    Given the TCP normalizer server is running on localhost
    When a client sends a valid Syslog CEF line:
      """
      <134>Dec 05 10:30:45 192.168.1.1 CEF:0|Microsoft|Windows|10.0|4624|An account was successfully logged on|1|src=10.0.50.42 suser=jsmith msg=An account was successfully logged on act=allow outcome=success
      """
    Then the output sink should receive a normalized log matching:
      | field          | value                                 |
      | event_type     | start                                 |
      | event_category | authentication                        |
      | event_outcome  | success                               |
      | source_ip      | 10.0.50.42                            |
      | user_name      | jsmith                                |
      | host_name      | 192.168.1.1                           |
      | log_level      | info                                  |
      | message        | An account was successfully logged on |

  Scenario: Ingest and parse a valid Windows Event NDJSON message over TCP
    Given the TCP normalizer server is running on localhost
    When a client sends a valid Windows Event NDJSON line:
      """
      {"System": {"EventID": 4624, "TimeCreated": "2026-02-14T14:22:10.8831200Z", "Computer": "dc01.contoso.local"}, "EventData": {"TargetUserName": "jsmith", "IpAddress": "10.0.50.42"}, "RenderingInfo": {"Message": "An account was successfully logged on.", "Level": "Information", "Keywords": ["Audit Success"]}}
      """
    Then the output sink should receive a normalized log matching:
      | field          | value                                 |
      | event_type     | start                                 |
      | event_category | authentication                        |
      | event_outcome  | success                               |
      | source_ip      | 10.0.50.42                            |
      | user_name      | jsmith                                |
      | host_name      | dc01.contoso.local                    |
      | log_level      | info                                  |
      | message        | An account was successfully logged on. |

  Scenario: Ingest a malformed log line over TCP
    Given the TCP normalizer server is running on localhost
    When a client sends a malformed log line:
      """
      {"invalid_json:
      """
    Then the server should capture the parsing error for that line
