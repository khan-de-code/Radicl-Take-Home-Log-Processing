"""Inbound CLI adapter using rich-click.

Defines the CLI command configurations and binds arguments to start the log normalizer daemon.
"""

import asyncio
import logging
import sys

import rich_click as click

from adapters.inbound.tcp_server import LogNormalizerTCPServer, create_ssl_context
from adapters.outbound.file_sink import LogNormalizerFileSink
from domain.models import NormalizedLog
from domain.parser import parse_line
from domain.utils import setup_logging

logger = logging.getLogger("log_normalizer")


async def stdout_sink(log: NormalizedLog) -> None:
    """Outbound port adapter that writes the normalized log to stdout as JSON."""
    sys.stdout.write(log.model_dump_json() + "\n")
    sys.stdout.flush()


async def error_handler(raw_line: str, error: Exception) -> None:
    """Outbound port adapter that logs parsing or decoding errors."""
    logger.error(
        "Failed to process log line: %s",
        error,
        extra={"raw_line": raw_line},
    )


async def run_server(
    port: int,
    output: str,
    tls_cert: str | None,
    tls_key: str | None,
    tls_ca: str | None,
) -> None:
    """Coroutine to construct and run the TCP server daemon.

    Args:
        port: Configured TCP port.
        output: Destination output path ('-' or file path).
        tls_cert: Server certificate file path.
        tls_key: Server private key file path.
        tls_ca: Client verification CA certificate path.
    """
    setup_logging()
    logger.info("Initializing Log Normalizer service...")

    # Wire outbound sink
    if output == "-":
        sink = stdout_sink
        file_sink_instance = None
    else:
        file_sink_instance = LogNormalizerFileSink(output)
        file_sink_instance.open()
        sink = file_sink_instance

    # Construct SSL context if TLS cert parameters are provided
    ssl_context = None
    if tls_cert and tls_key:
        try:
            ssl_context = create_ssl_context(tls_cert, tls_key, tls_ca)
            logger.info("SSL/TLS context loaded successfully.")
        except Exception as ssl_error:  # noqa: BLE001
            logger.critical("Failed to load SSL/TLS credentials: %s", ssl_error)
            if file_sink_instance:
                file_sink_instance.close()
            sys.exit(1)

    server = LogNormalizerTCPServer(
        host="127.0.0.1",
        port=port,
        parser=parse_line,
        sink=sink,
        on_error=error_handler,
        ssl_context=ssl_context,
    )

    try:
        await server.start()
        await server.serve_forever()
    except asyncio.CancelledError:
        logger.info("Service shutdown requested...")
    except Exception as error:
        logger.critical("Fatal exception during server execution", exc_info=error)
        sys.exit(1)
    finally:
        await server.stop()
        if file_sink_instance:
            file_sink_instance.close()


@click.command()
@click.option(
    "--port",
    default=5044,
    type=int,
    help="TCP port to bind and listen on (default: 5044).",
)
@click.option(
    "--output",
    default="-",
    type=str,
    help="Output destination path. Set to '-' for stdout (default: '-').",
)
@click.option(
    "--tls-cert",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to SSL/TLS server certificate file.",
)
@click.option(
    "--tls-key",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to SSL/TLS server key file.",
)
@click.option(
    "--tls-ca",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to CA certificate to enable mutual TLS client verification.",
)
def cli(
    port: int,
    output: str,
    tls_cert: str | None,
    tls_key: str | None,
    tls_ca: str | None,
) -> None:
    """Log Normalizer Service Daemon CLI interface."""
    # Validate TLS parameters (cert and key must be paired)
    if (tls_cert and not tls_key) or (tls_key and not tls_cert):
        click.echo("Error: Both --tls-cert and --tls-key must be provided for TLS.", err=True)
        sys.exit(1)

    try:
        asyncio.run(run_server(port, output, tls_cert, tls_key, tls_ca))
    except KeyboardInterrupt:
        logger.info("Service stopped by user request.")
        sys.exit(0)
