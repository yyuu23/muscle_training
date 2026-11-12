"""
Exports schemas (plan §6.4)
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ExportCreateResponse(BaseModel):
    job_id: uuid.UUID
    status: str


class ExportStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    download_url: str | None = None
    expires_at: datetime | None = None
    error_code: str | None = None
