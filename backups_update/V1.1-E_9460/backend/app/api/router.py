from fastapi import APIRouter

from backend.app.api.routes import admin, health, identity

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(identity.router)
api_router.include_router(admin.router)
