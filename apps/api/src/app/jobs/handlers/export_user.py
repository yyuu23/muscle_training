"""
User export job handler (plan §6.4 / §9.5)

Builds a JSON export of all user data, stores it with retention_class=export
(24h expiry), returns a short-lived download URL.
"""

import json
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.catalog import PlanVersion
from app.db.models.knowledge import Asset
from app.db.models.nutrition import MealLog, Measurement
from app.db.models.profile import MemoryCandidate, Profile, ProfileFact
from app.db.models.training import SessionExercise, WorkoutSession, WorkoutSet
from app.jobs.queue import complete_job, fail_job
from app.storage import get_storage

EXPORT_RETENTION_HOURS = 24


async def handle_user_export(db: AsyncSession, job) -> None:
    user_id = UUID(job.payload["user_id"])

    async def _all(model):
        rows = (
            await db.execute(select(model).where(model.user_id == user_id))
        ).scalars().all()
        return [r.__dict__.copy() for r in rows]

    try:
        export = {
            "exported_at": datetime.now(tz=None).isoformat(),
            "user_id": str(user_id),
            "profile": await _all(Profile),
            "profile_facts": await _all(ProfileFact),
            "memory_candidates": await _all(MemoryCandidate),
            "plan_versions": await _all(PlanVersion),
            "workout_sessions": await _all(WorkoutSession),
            "session_exercises": await _all(SessionExercise),
            "workout_sets": await _all(WorkoutSet),
            "measurements": await _all(Measurement),
            "meal_logs": await _all(MealLog),
        }

        # Clean non-serializable keys
        def clean(rows):
            cleaned = []
            for row in rows:
                item = {}
                for key, value in row.items():
                    if key == "_sa_instance_state":
                        continue
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    item[key] = str(value) if not isinstance(value, (str, int, float, bool, list, dict, type(None))) else value
                cleaned.append(item)
            return cleaned

        export = {table: clean(rows) for table, rows in export.items() if table not in ("exported_at", "user_id")}

        payload = json.dumps(
            {"exported_at": datetime.now(tz=None).isoformat(), "user_id": str(user_id), **export},
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")

        storage = get_storage()
        object_key = f"exports/{user_id}/{uuid4()}.json"
        await storage.put(object_key, payload, "application/json")

        expires_at = datetime.now(tz=None) + timedelta(hours=EXPORT_RETENTION_HOURS)
        db.add(
            Asset(
                owner_user_id=user_id,
                object_key=object_key,
                sha256=str(hash(payload)),
                mime_type="application/json",
                byte_size=len(payload),
                retention_class="export",
                status="verified",
                expires_at=expires_at,
            )
        )
        await db.commit()

        grant = await storage.grant_download(object_key, expires_seconds=600)
        await complete_job(
            db,
            job.id,
            {"download_url": grant.url, "expires_at": expires_at.isoformat(), "object_key": object_key},
        )
    except Exception as exc:  # noqa: BLE001
        await fail_job(db, job.id, error_code="EXPORT_ERROR", error_detail=str(exc)[:500])
