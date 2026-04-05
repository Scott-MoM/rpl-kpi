from pathlib import Path
import sys
import traceback

from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

print("[backend.app.main] module import start", file=sys.stderr, flush=True)

try:
    from .api.router import api_router
except BaseException:
    print("[backend.app.main] failed importing api_router", file=sys.stderr, flush=True)
    traceback.print_exc()
    raise

try:
    from .core.config import settings
except BaseException:
    print("[backend.app.main] failed importing settings", file=sys.stderr, flush=True)
    traceback.print_exc()
    raise


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
print(f"[backend.app.main] static dir={STATIC_DIR}", file=sys.stderr, flush=True)


def create_app() -> FastAPI:
    print("[backend.app.main] create_app start", file=sys.stderr, flush=True)
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

    print("[backend.app.main] including api router", file=sys.stderr, flush=True)
    app.include_router(api_router, prefix="/api")
    print("[backend.app.main] mounting static files", file=sys.stderr, flush=True)
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="frontend")
    print("[backend.app.main] create_app complete", file=sys.stderr, flush=True)
    return app


app = create_app()
print("[backend.app.main] module import complete", file=sys.stderr, flush=True)
