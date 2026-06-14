"""Outbound file sink adapter.

This module implements writing normalized logs to a local file.
"""

import asyncio
import logging
from pathlib import Path

from domain.models import NormalizedLog

logger = logging.getLogger("log_normalizer")


class LogNormalizerFileSink:
    """Outbound port adapter that writes normalized logs to a file."""

    def __init__(self, file_path: str) -> None:
        """Initialize the file sink with the target file path.

        Args:
            file_path: The file system path to append log records.
        """
        self.file_path = file_path
        self._file = None

    def open(self) -> None:
        """Open the target file for appending."""
        try:
            self._file = Path(self.file_path).open("a", encoding="utf-8")  # noqa: SIM115
        except OSError:
            logger.exception("Failed to open output file: %s", self.file_path)
            raise

    def close(self) -> None:
        """Close the file handle cleanly."""
        if self._file:
            try:
                self._file.close()
            except OSError:
                logger.exception("Error closing output file: %s", self.file_path)
            finally:
                self._file = None

    async def __call__(self, log: NormalizedLog) -> None:
        """Asynchronously write a NormalizedLog record to the file.

        Args:
            log: The validated NormalizedLog model instance.
        """
        if not self._file:
            self.open()

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write, log)

    def _write(self, log: NormalizedLog) -> None:
        """Synchronously write a log entry and flush to disk."""
        if self._file:
            self._file.write(log.model_dump_json() + "\n")
            self._file.flush()
