from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, use_enum_values=False)


class IdentifiedModel(DomainModel):
    id: UUID = Field(default_factory=uuid4)


class TimestampedModel(IdentifiedModel):
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


Metadata = dict[str, Any]
