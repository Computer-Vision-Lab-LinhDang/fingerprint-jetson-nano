"""API router exports for the worker application."""

from app.api.routers.models import router as models_router
from app.api.routers.sensor import router as sensor_router
from app.api.routers.system import router as system_router
from app.api.routers.users import router as users_router
from app.api.routers.verification import router as verification_router

__all__ = [
    "models_router",
    "sensor_router",
    "system_router",
    "users_router",
    "verification_router",
]
