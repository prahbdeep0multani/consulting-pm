import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str
    tenant_id: uuid.UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_service: str
    correlation_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    schema_version: str = "1.0"

    def to_stream_dict(self) -> dict[str, str]:
        return {"data": self.model_dump_json()}
