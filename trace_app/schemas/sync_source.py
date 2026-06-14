import datetime

from pydantic import BaseModel, ConfigDict


class SyncSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    provider: str
    last_sync_at: datetime.datetime | None = None
    created_at: datetime.datetime
