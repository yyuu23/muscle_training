"""Job status schemas (plan §6.4)."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.db.models.operations import JOB_STATUSES

JobStatusLiteral = Literal[*JOB_STATUSES]


class JobStatusResponse(BaseModel):
    """Own-job status; never exposes other users' jobs (404 instead)."""

    model_config = ConfigDict(from_attributes=True)

    job_id: str
    status: JobStatusLiteral
    phase: str | None = None
    error_code: str | None = None
    result_ref: dict[str, Any] | None = None
