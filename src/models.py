"""Pydantic model schemas for the Log Normalizer Service."""

import re

from pydantic import BaseModel, Field, field_validator

# ISO 8601 UTC format validator regex (e.g., 2026-06-14T03:52:44.123Z)
ISO8601_UTC_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


class NormalizedLog(BaseModel):
    """Normalized schema representation of a security log event."""

    timestamp: str = Field(..., alias="@timestamp")
    event_type: str = Field(..., alias="event.type")
    event_category: str = Field(..., alias="event.category")
    event_outcome: str = Field(..., alias="event.outcome")
    log_level: str = Field(..., alias="log.level")

    # Optional Fields (omitted if null or empty)
    source_ip: str | None = Field(None, alias="source.ip")
    user_name: str | None = Field(None, alias="user.name")
    host_name: str | None = Field(None, alias="host.name")
    message: str | None = Field(None, alias="message")

    class Config:
        """Configuration options for Pydantic."""

        populate_by_name = True
        extra = "ignore"

    @field_validator("timestamp")
    @classmethod
    def validate_iso8601_utc(cls, value: str) -> str:
        """Validate that the timestamp is a valid ISO 8601 UTC string."""
        if not ISO8601_UTC_REGEX.match(value):
            error_message = (
                f"Timestamp must be in ISO 8601 UTC format (YYYY-MM-DDTHH:MM:SS.mmmZ), got: {value}"
            )
            raise ValueError(error_message)
        return value
