from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="FastAPI backend for the Regional KPI Dashboard migration.",
        docs_url="/docs" if settings.api_docs_enabled else None,
        redoc_url="/redoc" if settings.api_docs_enabled else None,
        openapi_url="/openapi.json" if settings.api_docs_enabled else None,
    )

    if settings.force_https:
        app.add_middleware(HTTPSRedirectMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.allowed_hosts and settings.allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    @app.get("/health", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment, "app": settings.app_name}

    @app.get("/health/ready", tags=["system"])
    def readiness_check() -> JSONResponse:
        core_missing = settings.missing_core_settings
        admin_missing = settings.missing_admin_settings
        sync_missing = settings.missing_sync_settings
        is_ready = not core_missing
        payload = {
            "status": "ready" if is_ready else "not_ready",
            "environment": settings.environment,
            "checks": {
                "core": {"configured": not core_missing, "missing": core_missing},
                "admin": {"configured": not admin_missing, "missing": admin_missing},
                "sync": {"configured": not sync_missing, "missing": sync_missing},
            },
        }
        return JSONResponse(status_code=200 if is_ready else 503, content=payload)

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
