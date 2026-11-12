"""
Capability reporting (plan §6.2 GET /capabilities)

Reports whether model/content/storage are configured — never secrets.
Recording features must keep working when model keys are absent.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.catalog import Exercise, TrainingTemplate


def _model_configured() -> dict[str, bool]:
    settings = get_settings()
    has_key = bool(settings.dashscope_api_key)
    return {
        "chat_model_configured": has_key,
        "embedding_model_configured": has_key,
        "transcription_configured": has_key,
    }


def _storage_configured() -> bool:
    settings = get_settings()
    if settings.storage_backend == "filesystem":
        return True
    return bool(
        settings.oss_endpoint
        and settings.oss_access_key_id
        and settings.oss_access_key_secret
        and settings.oss_bucket_name
    )


async def content_ready(db: AsyncSession, include_fixtures: bool = False) -> bool:
    """At least one approved template + one approved exercise available."""
    template_q = select(func.count()).select_from(TrainingTemplate).where(
        TrainingTemplate.review_status == "approved"
    )
    exercise_q = select(func.count()).select_from(Exercise).where(
        Exercise.review_status == "approved"
    )
    if not include_fixtures:
        template_q = template_q.where(TrainingTemplate.fixture.is_(False))
        exercise_q = exercise_q.where(Exercise.fixture.is_(False))

    templates = (await db.execute(template_q)).scalar() or 0
    exercises = (await db.execute(exercise_q)).scalar() or 0
    return templates > 0 and exercises > 0


async def build_capabilities(db: AsyncSession | None = None) -> dict:
    """Build the capability snapshot. DB is optional for /auth/me speed."""
    caps = _model_configured()
    caps["storage_configured"] = _storage_configured()
    caps["content_ready"] = await content_ready(db) if db is not None else False
    caps["offline_recording_available"] = True
    return caps
