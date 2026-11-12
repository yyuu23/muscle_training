"""
API router configuration (plan §6)

All routers mount under /api/v1 (set in main.py).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.router import router as auth_router
from app.modules.catalog.admin_router import router as catalog_admin_router
from app.modules.catalog.router import router as catalog_router
from app.modules.conversations.router import router as conversations_router
from app.modules.deletion.router import router as deletion_router
from app.modules.exports.router import router as exports_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.measurements.router import router as measurements_router
from app.modules.nutrition.router import router as nutrition_router
from app.modules.plans.router import router as plans_router
from app.modules.profiles.router import router as profiles_router
from app.modules.reviews.router import router as reviews_router
from app.modules.sync.router import router as sync_router
from app.modules.workouts.router import router as workouts_router
from app.services.capabilities import build_capabilities

api_router = APIRouter()

# Auth & profile
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(profiles_router, prefix="/profiles", tags=["profiles"])

# Catalog: public reads + admin management
api_router.include_router(catalog_router, tags=["catalog"])
api_router.include_router(catalog_admin_router, prefix="/admin/catalog", tags=["admin"])

# Training & records
api_router.include_router(workouts_router, prefix="/workouts", tags=["workouts"])
api_router.include_router(plans_router, prefix="/plans", tags=["plans"])
api_router.include_router(measurements_router, prefix="/measurements", tags=["measurements"])
api_router.include_router(nutrition_router, tags=["nutrition"])

# Offline sync
api_router.include_router(sync_router, prefix="/sync", tags=["sync"])

# Knowledge & chat
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(conversations_router, tags=["conversations"])

# Reviews, jobs, exports, account deletion
api_router.include_router(reviews_router, prefix="/reviews", tags=["reviews"])
api_router.include_router(exports_router, prefix="/exports", tags=["exports"])
api_router.include_router(deletion_router, tags=["deletion"])


@api_router.get("/")
async def api_root():
    """API root endpoint"""
    return {
        "message": "Muscle Training Agent API",
        "version": "v1",
    }


@api_router.get("/capabilities")
async def capabilities(db: AsyncSession = Depends(get_db_session)):
    """Model/content/storage availability; never returns secrets (plan §6.2)."""
    return await build_capabilities(db)
