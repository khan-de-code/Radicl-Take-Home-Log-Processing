"""Domain ports for the log normalizer service.

This module defines callable type aliases that represent the inbound and outbound
ports for Hexagonal Architecture.
"""

from collections.abc import Callable, Coroutine

from domain.models import NormalizedLog

# Outbound Port: A sink that receives a normalized log and processes/persists it.
type LogSinkPort = Callable[[NormalizedLog], Coroutine[None, None, None]]

# Outbound Port: An error handler for reporting bad logs or processing errors.
type LogErrorHandlerPort = Callable[[str, Exception], Coroutine[None, None, None]]

# Inbound Port: Parses a raw log string line into a NormalizedLog.
type LogParserPort = Callable[[str], NormalizedLog | None]
