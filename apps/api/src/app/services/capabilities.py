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
    has_chat_key = bool(settings.dashscope_api_key)
    has_embedding_key = bool(settings.embedding_api_key or settings.dashscope_api_key)
    # Transcription stays DashScope-native (paraformer); a chat relay
    # without the official key cannot serve it.
    return {
        "chat_model_configured": has_chat_key,
        "embedding_model_configured": has_embedding_key,
        "transcription_configured": has_dashscope_native(settings),
    }


def has_dashscope_native(settings) -> bool:
    """Whether the official DashScope endpoint is reachable for native
    features (paraformer ASR)."""
    return bool(settings.dashscope_api_key) and "dashscope.aliyuncs.com" in settings.dashscope_base_url


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
