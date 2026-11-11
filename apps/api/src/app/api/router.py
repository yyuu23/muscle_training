"""
API router configuration
"""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.profiles.router import router as profiles_router
from app.modules.workouts.router import router as workouts_router

api_router = APIRouter()

# Include module routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
api_router.include_router(workouts_router, prefix="/workouts", tags=["workouts"])


@api_router.get("/")
async def api_root():
    """API root endpoint"""
    return {
        "message": "Muscle Training Agent API",
        "version": "v1",
    }
