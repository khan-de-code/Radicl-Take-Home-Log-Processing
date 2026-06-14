"""General utilities for the Log Normalizer Service."""

import datetime
import json
import logging
import sys
import time
from typing import Any


class JSONFormatter(logging.Formatter):
    """Custom logging formatter that outputs records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.datetime.fromtimestamp(record.created, tz=datetime.UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging outputting JSON to stderr.

    Args:
        level: The logging level threshold (e.g., 'INFO', 'WARNING').
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)


def adjust_syslog_year(  # noqa: PLR0913
    month: str,
    day: int,
    hour: int,
    minute: int,
    second: int,
    system_clock: datetime.datetime,
) -> datetime.datetime:
    """Adjust syslog timestamp lacking a year to prevent future dates.

    Assumes the current UTC year, but subtracts one year if the parsed date
    is > 7 days in the future relative to the system clock.

    Args:
        month: The English three-letter month name (e.g., 'Dec').
        day: The day of the month.
        hour: The hour.
        minute: The minute.
        second: The second.
        system_clock: The current system time to compare against.

    Returns:
        The adjusted timezone-aware datetime.

    Raises:
        ValueError: If the month name is invalid.
    """
    try:
        month_num = time.strptime(month[:3].title(), "%b").tm_mon
    except ValueError as error:
        error_message = f"Invalid month name: {month}"
        raise ValueError(error_message) from error

    year = system_clock.year
    if month_num == 2 and day == 29:  # noqa: PLR2004
        while not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
            year -= 1
    try:
        parsed_date = datetime.datetime(
            year, month_num, day, hour, minute, second, tzinfo=datetime.UTC
        )
    except ValueError:
        # Handle Feb 29 leap-year edge cases on non-leap years
        parsed_date = datetime.datetime(
            year - 1, month_num, day, hour, minute, second, tzinfo=datetime.UTC
        )

    # Roll back 1 year if the date is more than 7 days in the future
    if parsed_date > system_clock + datetime.timedelta(days=7):
        try:
            parsed_date = parsed_date.replace(year=year - 1)
        except ValueError:
            # Handle leap year rollover constraints
            parsed_date = datetime.datetime(
                year - 1, month_num, day - 1, hour, minute, second, tzinfo=datetime.UTC
            )

    return parsed_date
