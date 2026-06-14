"""Inbound TCP server adapter.

This module implements the TCP daemon that listens for raw log lines,
parses them using a domain parser port, and sends normalized logs to a sink port.
"""

import asyncio
import contextlib
import logging
from collections.abc import Coroutine

from domain.ports import LogErrorHandlerPort, LogParserPort, LogSinkPort

logger = logging.getLogger("log_normalizer")


class LogNormalizerTCPServer:
    """Asynchronous TCP server that listens for incoming log lines.

    Each client connection is handled concurrently. Raw lines are parsed and
    routed to the configured LogSinkPort. Errors are routed to LogErrorHandlerPort.
    """

    def __init__(
        self,
        host: str,
        port: int,
        parser: LogParserPort,
        sink: LogSinkPort,
        on_error: LogErrorHandlerPort,
    ) -> None:
        """Initialize the TCP server adapter with dependencies.

        Args:
            host: Interface address to bind to.
            port: Port to listen on.
            parser: Domain parser to parse raw lines.
            sink: Outbound sink to route normalized logs.
            on_error: Outbound port to handle processing errors.
        """
        self.host = host
        self.port = port
        self.parser = parser
        self.sink = sink
        self.on_error = on_error
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        """Start the asynchronous TCP server and begin accepting connections."""
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
        )
        addr = self._server.sockets[0].getsockname()
        logger.info("TCP Server listening on %s", addr)

    async def stop(self) -> None:
        """Gracefully shut down the TCP server, closing all active connections."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("TCP Server stopped")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle an individual client connection lifecycle.

        Args:
            reader: StreamReader to read raw data from client.
            writer: StreamWriter to write responses or manage connection lifecycle.
        """
        client_address = writer.get_extra_info("peername")
        logger.debug("New connection from %s", client_address)
        try:
            while True:
                line_bytes = await reader.readline()
                if not line_bytes:
                    break

                try:
                    line = line_bytes.decode("utf-8").strip()
                except UnicodeDecodeError as decode_error:
                    await self.on_error(line_bytes.decode("utf-8", errors="replace"), decode_error)
                    continue

                if not line:
                    continue

                await self._process_line(line)
        except asyncio.CancelledError:
            logger.debug("Connection task cancelled for client %s", client_address)
        except Exception as error:
            logger.exception("Unexpected client error from %s", client_address)
            await self.on_error("", error)
        finally:
            writer.close()
            with contextlib.suppress(ConnectionError):
                await writer.wait_closed()
            logger.debug("Closed connection from %s", client_address)

    async def _process_line(self, line: str) -> None:
        """Parse and process a single log line.

        Args:
            line: Stripped raw string line.
        """
        try:
            normalized = self.parser(line)
            if normalized:
                await self.sink(normalized)
        except Exception as error:  # noqa: BLE001
            await self.on_error(line, error)

    def serve_forever(self) -> Coroutine[None, None, None]:
        """Return a coroutine that runs until the server is explicitly stopped.

        Returns:
            A coroutine that can be awaited or run via asyncio.run().

        Raises:
            RuntimeError: If server has not been started yet.
        """
        if not self._server:
            msg = "Server must be started before calling serve_forever"
            raise RuntimeError(msg)
        return self._server.serve_forever()
