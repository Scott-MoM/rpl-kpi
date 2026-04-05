from fastapi import APIRouter

from app.api.routes import admin, auth, case_studies, dashboards, reports

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboards.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(case_studies.router, prefix="/case-studies", tags=["case-studies"])
