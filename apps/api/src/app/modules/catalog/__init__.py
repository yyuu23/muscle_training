"""
Catalog module - Exercise and Template management
"""

from app.modules.catalog.router import router
from app.modules.catalog.schemas import ExerciseResponse, TemplateResponse
from app.modules.catalog.service import CatalogService

__all__ = [
    'router',
    'CatalogService',
    'ExerciseResponse',
    'TemplateResponse',
]
