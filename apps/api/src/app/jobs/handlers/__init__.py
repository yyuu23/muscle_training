"""
Job handlers registry (plan §9.1)
"""

from app.jobs.handlers.delete_user import handle_user_delete
from app.jobs.handlers.export_user import handle_user_export
from app.jobs.handlers.generate_plan import handle_plan_generate
from app.jobs.handlers.import_knowledge import handle_import
from app.jobs.handlers.knowledge_index import handle_knowledge_index
from app.jobs.handlers.maintenance import handle_maintenance
from app.jobs.handlers.weekly_review import handle_weekly_review

HANDLERS = {
    "knowledge_import": handle_import,
    "knowledge_index": handle_knowledge_index,
    "plan_generate": handle_plan_generate,
    "weekly_review": handle_weekly_review,
    "user_export": handle_user_export,
    "user_delete": handle_user_delete,
    "temporary_asset_cleanup": handle_maintenance,
}

# Media jobs run with concurrency 1; generation jobs concurrency 2 (plan §9.1)
MEDIA_JOBS = {"knowledge_import", "knowledge_index"}
GENERATION_JOBS = {"plan_generate", "weekly_review", "user_export", "user_delete"}

__all__ = [
    "HANDLERS",
    "MEDIA_JOBS",
    "GENERATION_JOBS",
    "handle_import",
    "handle_knowledge_index",
    "handle_plan_generate",
    "handle_weekly_review",
    "handle_user_export",
    "handle_user_delete",
    "handle_maintenance",
]
