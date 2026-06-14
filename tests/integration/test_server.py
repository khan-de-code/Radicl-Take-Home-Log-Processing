"""Integration tests using pytest-bdd for TCP server ingestion scenarios."""

import asyncio
import contextlib
from typing import Any

from pytest_bdd import given, scenario, then, when

from adapters.inbound.tcp_server import LogNormalizerTCPServer
from domain.models import NormalizedLog
from domain.parser import parse_line

EXPECTED_DATATABLE_COLS = 2


@scenario(
    "features/ingestion.feature", "Ingest and parse a valid RFC 3164 Syslog CEF message over TCP"
)
def test_ingestion() -> None:
    """Entry point for pytest-bdd scenario."""


@scenario(
    "features/ingestion.feature", "Ingest and parse a valid Windows Event NDJSON message over TCP"
)
def test_ingestion_windows_json() -> None:
    """Entry point for Windows JSON scenario."""


@scenario("features/ingestion.feature", "Ingest a malformed log line over TCP")
def test_ingestion_malformed() -> None:
    """Entry point for malformed log scenario."""


@given("the TCP normalizer server is running on localhost", target_fixture="server_context")
def step_server_running() -> dict[str, Any]:
    """Fixture: Start the TCP normalizer server.

    Returns:
        A dictionary containing server state context.
    """
    received_logs: list[NormalizedLog] = []
    received_errors: list[tuple[str, Exception]] = []

    async def mock_sink(log: NormalizedLog) -> None:
        received_logs.append(log)

    async def mock_error_handler(raw_line: str, error: Exception) -> None:
        received_errors.append((raw_line, error))

    server = LogNormalizerTCPServer(
        host="127.0.0.1",
        port=0,
        parser=parse_line,
        sink=mock_sink,
        on_error=mock_error_handler,
    )

    # Setup clean independent event loop for this test scenario
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.start())

    sockets = server.sockets
    assert len(sockets) > 0
    actual_port = sockets[0].getsockname()[1]
    server_task = loop.create_task(server.serve_forever())

    return {
        "server": server,
        "port": actual_port,
        "task": server_task,
        "received_logs": received_logs,
        "received_errors": received_errors,
        "loop": loop,
    }


def _send_text(server_context: dict[str, Any], text: str) -> None:
    port = server_context["port"]
    log_line = text.strip() + "\n"

    async def _send() -> None:
        _, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(log_line.encode("utf-8"))
        await writer.drain()
        await asyncio.sleep(0.1)
        writer.close()
        await writer.wait_closed()

    server_context["loop"].run_until_complete(_send())


@when("a client sends a valid Syslog CEF line:")
def step_send_line(server_context: dict[str, Any], docstring: str) -> None:
    """Send log line to the running server.

    Args:
        server_context: The server state context dictionary.
        docstring: The docstring content passed by pytest-bdd.
    """
    _send_text(server_context, docstring)


@when("a client sends a valid Windows Event NDJSON line:")
def step_send_windows_line(server_context: dict[str, Any], docstring: str) -> None:
    """Send log line to the running server.

    Args:
        server_context: The server state context dictionary.
        docstring: The docstring content passed by pytest-bdd.
    """
    _send_text(server_context, docstring)


@when("a client sends a malformed log line:")
def step_send_malformed_line(server_context: dict[str, Any], docstring: str) -> None:
    """Send log line to the running server.

    Args:
        server_context: The server state context dictionary.
        docstring: The docstring content passed by pytest-bdd.
    """
    _send_text(server_context, docstring)


@then("the output sink should receive a normalized log matching:")
def step_verify_log(server_context: dict[str, Any], datatable: list[list[str]]) -> None:
    """Assert fields of the parsed log record match expectations.

    Args:
        server_context: The server state context dictionary.
        datatable: The Gherkin datatable object passed by pytest-bdd.
    """
    loop = server_context["loop"]
    # Shutdown the server
    server_context["task"].cancel()

    async def _stop() -> None:
        with contextlib.suppress(asyncio.CancelledError):
            await server_context["task"]
        await server_context["server"].stop()

    loop.run_until_complete(_stop())

    received_logs = server_context["received_logs"]
    assert len(received_logs) == 1
    log = received_logs[0]

    # Parse Gherkin datatable
    expected_values = {}
    for row in datatable[1:]:
        if len(row) == EXPECTED_DATATABLE_COLS:
            expected_values[row[0]] = row[1]

    assert log.event_type == expected_values["event_type"]
    assert log.event_category == expected_values["event_category"]
    assert log.event_outcome == expected_values["event_outcome"]
    assert log.source_ip == expected_values["source_ip"]
    assert log.user_name == expected_values["user_name"]
    assert log.host_name == expected_values["host_name"]
    assert log.log_level == expected_values["log_level"]
    assert log.message == expected_values["message"]


@then("the server should capture the parsing error for that line")
def step_verify_error(server_context: dict[str, Any]) -> None:
    """Verify that parsing error was captured.

    Args:
        server_context: The server state context dictionary.
    """
    loop = server_context["loop"]
    server_context["task"].cancel()

    async def _stop() -> None:
        with contextlib.suppress(asyncio.CancelledError):
            await server_context["task"]
        await server_context["server"].stop()

    loop.run_until_complete(_stop())

    received_errors = server_context["received_errors"]
    assert len(received_errors) == 1
    raw_line, error = received_errors[0]
    assert raw_line == '{"invalid_json:'
    assert isinstance(error, ValueError)
