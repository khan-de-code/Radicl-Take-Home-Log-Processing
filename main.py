"""Main application entry point.

Wires ports and adapters and bootstraps the Log Normalizer service.
"""

import asyncio
import logging
import sys

from adapters.inbound.tcp_server import LogNormalizerTCPServer
from domain.models import NormalizedLog
from domain.parser import parse_line
from domain.utils import setup_logging

logger = logging.getLogger("log_normalizer")


async def stdout_sink(log: NormalizedLog) -> None:
    """Outbound port adapter that writes the normalized log to stdout as JSON.

    Args:
        log: The validated NormalizedLog model instance.
    """
    sys.stdout.write(log.model_dump_json() + "\n")
    sys.stdout.flush()


async def error_handler(raw_line: str, error: Exception) -> None:
    """Outbound port adapter that logs parsing or decoding errors.

    Args:
        raw_line: The raw input string that caused the failure.
        error: The exception encountered.
    """
    logger.error(
        "Failed to process log line: %s",
        error,
        extra={"raw_line": raw_line},
    )


async def main() -> None:
    """Bootstrap the Log Normalizer service."""
    setup_logging()
    logger.info("Initializing Log Normalizer service...")

    # NOTE: Port should be configurable via config files or env variables in the future.
    # Bind to localhost:5140 for local ingestion daemon.
    server = LogNormalizerTCPServer(
        host="127.0.0.1",
        port=5140,
        parser=parse_line,
        sink=stdout_sink,
        on_error=error_handler,
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


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by user request.")
        sys.exit(0)
