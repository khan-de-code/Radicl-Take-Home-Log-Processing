# Data Models: Log Normalizer Service

This document defines the data structures and validation constraints for the Log Normalizer service.

## 1. Output Schema Model (`NormalizedLog`)

The output schema is represented by the `NormalizedLog` Pydantic model. It maps directly to the target schema defined in `SCHEMA.md`.

### Pydantic Struct Definition

```python
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re

# ISO 8601 UTC format validator regex (e.g., 2026-06-14T03:52:44.123Z)
ISO8601_UTC_REGEX = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
)

class NormalizedLog(BaseModel):
    timestamp: str = Field(..., alias="@timestamp")
    event_type: str = Field(..., alias="event.type")
    event_category: str = Field(..., alias="event.category")
    event_outcome: str = Field(..., alias="event.outcome")
    log_level: str = Field(..., alias="log.level")
    
    # Optional Fields (omitted if null or empty)
    source_ip: Optional[str] = Field(None, alias="source.ip")
    user_name: Optional[str] = Field(None, alias="user.name")
    host_name: Optional[str] = Field(None, alias="host.name")
    message: Optional[str] = Field(None, alias="message")

    class Config:
        populate_by_name = True
        extra = "ignore"

    @field_validator("timestamp")
    @classmethod
    def validate_iso8601_utc(cls, value: str) -> str:
        if not ISO8601_UTC_REGEX.match(value):
            raise ValueError(
                f"Timestamp must be in ISO 8601 UTC format (YYYY-MM-DDTHH:MM:SS.mmmZ), got: {value}"
            )
        return value
```

### Filtering Rules
- Any source field mapped to an optional property that contains a value of `-` or `S-1-0-0` (sentinel value representing null) **must be set to None** so that it is excluded from the final output JSON.
- Output serialization should use `model_dump_json(by_alias=True, exclude_none=True)` to ensure fields like `source.ip` are serialized with a dot (`.`) and excluded entirely if they are `None`.

---

## 2. Ingestion Connection Tracker (`IngestionClient`)

To manage system constraints (concurrent connection caps and logging), each active TCP socket is tracked using a local dataclass or lightweight model.

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class IngestionClient:
    client_id: str             # "ip:port"
    host_ip: str
    port: int
    connected_at: datetime
    bytes_read: int = 0
    consecutive_failures: int = 0
    is_active: bool = True
```
