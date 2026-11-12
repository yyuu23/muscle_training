"""
Catalog service (plan §10.1 / §10.2)

- Content YAML files are validated before import.
- Import never self-marks review complete: review_status stays draft
  until an admin approves (reviewer/time/version written by the review op).
- Fixture content is excluded from production answers.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

import yaml
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.catalog import Exercise, TrainingTemplate
from app.modules.catalog.schemas import ContentValidationIssue

EXERCISE_REQUIRED_FIELDS = [
    "schema_version",
    "slug",
    "content_version",
    "display_name",
    "movement_pattern",
    "metric_type",
    "load_mode",
]
TEMPLATE_REQUIRED_FIELDS = [
    "schema_version",
    "slug",
    "content_version",
    "display_name",
    "sessions_per_week",
    "session_slots",
    "progression_policy",
]

LOAD_MODES = {"total_external", "per_implement", "bodyweight", "assistance", "band"}
METRIC_TYPES = {"reps", "duration"}


def _stable_exercise_id(slug: str, content_version: int) -> UUID:
    """Deterministic exercise id per (slug, content_version)."""
    return uuid5(NAMESPACE_URL, f"exercise:{slug}:{content_version}")


def _stable_template_id(slug: str, content_version: int) -> UUID:
    return uuid5(NAMESPACE_URL, f"template:{slug}:{content_version}")


def validate_exercise_document(doc: dict) -> list[ContentValidationIssue]:
    """Validate one exercise YAML document (plan §10.1)."""
    issues: list[ContentValidationIssue] = []

    for field in EXERCISE_REQUIRED_FIELDS:
        if field not in doc:
            issues.append(
                ContentValidationIssue(code="missing_field", message=f"缺少字段 {field}", path=field)
            )
    if issues:
        return issues

    slug = str(doc["slug"])
    if not slug or not slug.replace("-", "").replace("_", "").isalnum():
        issues.append(ContentValidationIssue(code="invalid_slug", message=f"slug 不合法: {slug}", path="slug"))

    if doc["metric_type"] not in METRIC_TYPES:
        issues.append(
            ContentValidationIssue(
                code="invalid_metric_type", message=f"metric_type 必须是 {METRIC_TYPES}", path="metric_type"
            )
        )
    if doc["load_mode"] not in LOAD_MODES:
        issues.append(
            ContentValidationIssue(
                code="invalid_load_mode", message=f"load_mode 必须是 {LOAD_MODES}", path="load_mode"
            )
        )
    if not isinstance(doc["content_version"], int) or doc["content_version"] < 1:
        issues.append(
            ContentValidationIssue(code="invalid_version", message="content_version 必须是正整数", path="content_version")
        )

    for key in ("instructions", "common_errors", "aliases", "approved_alternatives", "evidence_refs"):
        if key in doc and not isinstance(doc[key], list):
            issues.append(
                ContentValidationIssue(code="invalid_list", message=f"{key} 必须是列表", path=key)
            )
    if "fixture" in doc and not isinstance(doc["fixture"], bool):
        issues.append(ContentValidationIssue(code="invalid_fixture", message="fixture 必须是布尔值", path="fixture"))

    return issues


def validate_template_document(doc: dict) -> list[ContentValidationIssue]:
    """Validate one template YAML document (plan §10.2)."""
    issues: list[ContentValidationIssue] = []

    for field in TEMPLATE_REQUIRED_FIELDS:
        if field not in doc:
            issues.append(
                ContentValidationIssue(code="missing_field", message=f"缺少字段 {field}", path=field)
            )
    if issues:
        return issues

    if not isinstance(doc["sessions_per_week"], int) or not 1 <= doc["sessions_per_week"] <= 7:
        issues.append(
            ContentValidationIssue(
                code="invalid_sessions", message="sessions_per_week 必须在 1-7", path="sessions_per_week"
            )
        )
    if not isinstance(doc["session_slots"], list) or not doc["session_slots"]:
        issues.append(
            ContentValidationIssue(code="invalid_slots", message="session_slots 必须是非空列表", path="session_slots")
        )
    if doc["progression_policy"] not in ("hold", "double_progression_v1"):
        issues.append(
            ContentValidationIssue(
                code="invalid_progression",
                message="progression_policy 只支持 hold / double_progression_v1",
                path="progression_policy",
            )
        )
    return issues


class CatalogService:
    """Exercise and template catalog"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Public reads
    # ------------------------------------------------------------------

    async def list_exercises(
        self, search: str | None = None, movement_pattern: str | None = None
    ) -> list[Exercise]:
        """Approved exercises; fixtures excluded in production."""
        query = select(Exercise).where(Exercise.review_status == "approved")
        if get_settings().python_env == "production":
            query = query.where(Exercise.fixture.is_(False))
        if search:
            query = query.where(Exercise.name.ilike(f"%{search}%"))
        if movement_pattern:
            query = query.where(Exercise.movement_pattern == movement_pattern)

        result = await self.db.execute(query.order_by(Exercise.name))
        return list(result.scalars().all())

    async def get_exercise(self, exercise_id: UUID) -> Exercise | None:
        return await self.db.get(Exercise, exercise_id)

    async def list_templates(self, sessions_per_week: int | None = None) -> list[TrainingTemplate]:
        query = select(TrainingTemplate).where(TrainingTemplate.review_status == "approved")
        if get_settings().python_env == "production":
            query = query.where(TrainingTemplate.fixture.is_(False))
        if sessions_per_week is not None:
            query = query.where(TrainingTemplate.sessions_per_week == sessions_per_week)

        result = await self.db.execute(query.order_by(TrainingTemplate.sessions_per_week))
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Import & validation (admin)
    # ------------------------------------------------------------------

    async def import_content(
        self, content_root: str, kind: str
    ) -> tuple[int, int, list[ContentValidationIssue]]:
        """Import YAML files from content/<kind>/*.yaml. Returns (imported, skipped, issues)."""
        root = Path(content_root).resolve()
        directory = root / kind
        if not directory.exists():
            return 0, 0, [
                ContentValidationIssue(code="missing_directory", message=f"目录不存在: {directory}")
            ]

        imported = 0
        skipped = 0
        issues: list[ContentValidationIssue] = []

        for file_path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
            try:
                doc = yaml.safe_load(file_path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                issues.append(
                    ContentValidationIssue(
                        code="yaml_error", message=f"{file_path.name}: {exc}", path=file_path.name
                    )
                )
                continue

            if not isinstance(doc, dict):
                issues.append(
                    ContentValidationIssue(
                        code="invalid_document", message=f"{file_path.name} 不是对象", path=file_path.name
                    )
                )
                continue

            doc_issues = (
                validate_exercise_document(doc)
                if kind == "exercises"
                else validate_template_document(doc)
            )
            if doc_issues:
                issues.extend(doc_issues)
                skipped += 1
                continue

            if kind == "exercises":
                await self._upsert_exercise(doc)
            else:
                await self._upsert_template(doc)
            imported += 1

        await self.db.commit()
        return imported, skipped, issues

    async def validate_content(
        self, content_root: str, kind: str
    ) -> list[ContentValidationIssue]:
        """Validate without importing."""
        root = Path(content_root).resolve()
        directory = root / kind
        issues: list[ContentValidationIssue] = []
        if not directory.exists():
            return [
                ContentValidationIssue(code="missing_directory", message=f"目录不存在: {directory}")
            ]

        # Referenced alternatives must exist (plan §10.1)
        slugs: set[str] = set()
        docs: list[dict] = []
        for file_path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
            try:
                doc = yaml.safe_load(file_path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                issues.append(
                    ContentValidationIssue(
                        code="yaml_error", message=f"{file_path.name}: {exc}", path=file_path.name
                    )
                )
                continue
            if isinstance(doc, dict):
                docs.append(doc)
                if "slug" in doc:
                    slugs.add(str(doc["slug"]))

        for doc in docs:
            doc_issues = (
                validate_exercise_document(doc) if kind == "exercises" else validate_template_document(doc)
            )
            issues.extend(doc_issues)

        if kind == "exercises":
            for doc in docs:
                for alt in doc.get("approved_alternatives", []) or []:
                    if alt not in slugs:
                        issues.append(
                            ContentValidationIssue(
                                code="missing_alternative",
                                message=f"{doc.get('slug')}: 替代动作 {alt} 不存在",
                                path=str(doc.get("slug")),
                            )
                        )
        return issues

    async def _upsert_exercise(self, doc: dict) -> Exercise:
        slug = str(doc["slug"])
        version = int(doc["content_version"])
        exercise_id = _stable_exercise_id(slug, version)

        existing = await self.db.get(Exercise, exercise_id)
        if existing is not None:
            return existing  # immutable content versions

        exercise = Exercise(
            id=exercise_id,
            slug=slug,
            content_version=version,
            name=str(doc["display_name"]),
            aliases=doc.get("aliases", []),
            movement_pattern=doc.get("movement_pattern"),
            equipment_tags=doc.get("required_equipment", []),
            metric_type=doc["metric_type"],
            load_mode=doc["load_mode"],
            instructions=doc.get("instructions", []),
            common_errors=doc.get("common_errors", []),
            approved_alternatives=doc.get("approved_alternatives", []),
            evidence_refs=doc.get("evidence_refs", []),
            review_status="draft",  # import never self-approves
            fixture=bool(doc.get("fixture", False)),
        )
        self.db.add(exercise)
        await self.db.flush()
        return exercise

    async def _upsert_template(self, doc: dict) -> TrainingTemplate:
        slug = str(doc["slug"])
        version = int(doc["content_version"])
        template_id = _stable_template_id(slug, version)

        existing = await self.db.get(TrainingTemplate, template_id)
        if existing is not None:
            return existing

        template = TrainingTemplate(
            id=template_id,
            slug=slug,
            content_version=version,
            name=str(doc["display_name"]),
            intended_population=doc.get("intended_population"),
            sessions_per_week=int(doc["sessions_per_week"]),
            required_intake_fields=doc.get("required_intake_fields", []),
            eligibility=doc.get("eligibility", {}),
            session_slots=doc.get("session_slots", []),
            allowed_exercise_ids=doc.get("allowed_exercise_ids", []),
            allowed_set_ranges=doc.get("allowed_set_ranges", {}),
            allowed_rep_ranges=doc.get("allowed_rep_ranges", {}),
            allowed_rest_ranges=doc.get("allowed_rest_ranges", {}),
            target_rir_ranges=doc.get("target_rir_ranges", {}),
            progression_policy=str(doc["progression_policy"]),
            time_estimation_parameters=doc.get("time_estimation_parameters", {}),
            approved_short_session_variants=doc.get("approved_short_session_variants", []),
            evidence_refs=doc.get("evidence_refs", []),
            review_status="draft",
            fixture=bool(doc.get("fixture", False)),
        )
        self.db.add(template)
        await self.db.flush()
        return template

    # ------------------------------------------------------------------
    # Review (admin)
    # ------------------------------------------------------------------

    async def review_exercise(
        self, exercise_id: UUID, admin_id: UUID, decision: str
    ) -> Exercise | None:
        exercise = await self.db.get(Exercise, exercise_id)
        if exercise is None:
            return None
        exercise.review_status = "approved" if decision == "approve" else "rejected"
        exercise.reviewed_by = admin_id
        exercise.reviewed_at = datetime.now(tz=None)
        await self.db.commit()
        await self.db.refresh(exercise)
        return exercise

    async def review_template(
        self, template_id: UUID, admin_id: UUID, decision: str
    ) -> TrainingTemplate | None:
        template = await self.db.get(TrainingTemplate, template_id)
        if template is None:
            return None
        template.review_status = "approved" if decision == "approve" else "rejected"
        template.reviewed_by = admin_id
        template.reviewed_at = datetime.now(tz=None)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def list_all_content(self, kind: str, review_status: str | None = None):
        model = Exercise if kind == "exercises" else TrainingTemplate
        query = select(model)
        if review_status:
            query = query.where(model.review_status == review_status)
        result = await self.db.execute(query.order_by(model.slug, model.content_version.desc()))
        return list(result.scalars().all())

    async def content_stats(self) -> dict:
        ex_total = (
            await self.db.execute(select(func.count()).select_from(Exercise))
        ).scalar()
        ex_approved = (
            await self.db.execute(
                select(func.count())
                .select_from(Exercise)
                .where(Exercise.review_status == "approved")
                .where(Exercise.fixture.is_(False))
            )
        ).scalar()
        tp_total = (
            await self.db.execute(select(func.count()).select_from(TrainingTemplate))
        ).scalar()
        tp_approved = (
            await self.db.execute(
                select(func.count())
                .select_from(TrainingTemplate)
                .where(TrainingTemplate.review_status == "approved")
                .where(TrainingTemplate.fixture.is_(False))
            )
        ).scalar()
        return {
            "exercises_total": ex_total,
            "exercises_approved": ex_approved,
            "templates_total": tp_total,
            "templates_approved": tp_approved,
            "content_ready": ex_approved > 0 and tp_approved > 0,
        }


def content_hash(doc: dict) -> str:
    """Stable hash of a content document."""
    canonical = json.dumps(doc, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
