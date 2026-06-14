"""Inbound TCP server adapter.

This module implements the TCP daemon that listens for raw log lines,
parses them using a domain parser port, and sends normalized logs to a sink port.
"""

import asyncio
import contextlib
import logging
import ssl
from collections.abc import Coroutine
from typing import Any

from domain.ports import LogErrorHandlerPort, LogParserPort, LogSinkPort

logger = logging.getLogger("log_normalizer")


class LogNormalizerTCPServer:
    """Asynchronous TCP server that listens for incoming log lines.

    Each client connection is handled concurrently. Raw lines are parsed and
    routed to the configured LogSinkPort. Errors are routed to LogErrorHandlerPort.
    """

    def __init__(  # noqa: PLR0913
        self,
        host: str,
        port: int,
        parser: LogParserPort,
        sink: LogSinkPort,
        on_error: LogErrorHandlerPort,
        ssl_context: ssl.SSLContext | None = None,
        max_connections: int = 100,
        idle_timeout: float = 30.0,
    ) -> None:
        """Initialize the TCP server adapter with dependencies.

        Args:
            host: Interface address to bind to.
            port: Port to listen on.
            parser: Domain parser to parse raw lines.
            sink: Outbound sink to route normalized logs.
            on_error: Outbound port to handle processing errors.
            ssl_context: Optional SSLContext to configure TLS.
            max_connections: Maximum limit of concurrent connections.
            idle_timeout: Inactivity timeout in seconds.
        """
        self.host = host
        self.port = port
        self.parser = parser
        self.sink = sink
        self.on_error = on_error
        self.ssl_context = ssl_context
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self._server: asyncio.AbstractServer | None = None
        self._active_connections = 0

    async def start(self) -> None:
        """Start the asynchronous TCP server and begin accepting connections."""
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
            ssl=self.ssl_context,
            limit=65536,
        )
        addr = self._server.sockets[0].getsockname()
        logger.info("TCP Server listening on %s", addr)

    @property
    def sockets(self) -> list[Any]:
        """Return sockets that the server is currently listening on.

        Returns:
            A list of socket objects, or empty list if not running.
        """
        if self._server:
            return self._server.sockets
        return []

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
        if self._active_connections >= self.max_connections:
            logger.warning(
                "Rejected connection from %s: max connections (%d) reached.",
                client_address,
                self.max_connections,
            )
            writer.close()
            with contextlib.suppress(ConnectionError):
                await writer.wait_closed()
            return

        self._active_connections += 1
        logger.debug(
            "New connection from %s (Active: %d)",
            client_address,
            self._active_connections,
        )
        try:
            while True:
                try:
                    # Enforce read timeout per line
                    line_bytes = await asyncio.wait_for(
                        reader.readline(),
                        timeout=self.idle_timeout,
                    )
                except (asyncio.LimitOverrunError, ValueError) as buffer_error:
                    logger.warning(
                        "Client %s exceeded maximum line length limit (64KB): %s",
                        client_address,
                        buffer_error,
                    )
                    break
                except TimeoutError:
                    logger.warning(
                        "Client %s timed out due to inactivity (idle timeout).",
                        client_address,
                    )
                    break

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
            self._active_connections -= 1
            writer.close()
            with contextlib.suppress(ConnectionError):
                await writer.wait_closed()
            logger.debug(
                "Closed connection from %s (Active: %d)",
                client_address,
                self._active_connections,
            )

    async def _process_line(self, line: str) -> None:
        """Parse and process a single log line.

        Args:
            line: Stripped raw string line.
        """
        try:
            normalized = self.parser(line)
        except Exception as error:  # noqa: BLE001
            await self.on_error(line, error)
            return

        if normalized:
            try:
                await self.sink(normalized)
            except Exception as error:  # noqa: BLE001
                await self.on_error(line, error)
        else:
            error_msg = "Malformed or unsupported log format"
            await self.on_error(line, ValueError(error_msg))

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


def create_ssl_context(
    cert_path: str | None,
    key_path: str | None,
    ca_path: str | None = None,
) -> ssl.SSLContext | None:
    """Create an SSLContext for the TCP server.

    If mutual TLS (mTLS) CA path is provided, client certificate verification is enforced.
    """
    if not cert_path or not key_path:
        return None

    # Server side context
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=cert_path, keyfile=key_path)

    if ca_path:
        context.load_verify_locations(cafile=ca_path)
        context.verify_mode = ssl.CERT_REQUIRED

    return context
