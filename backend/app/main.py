from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router
from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging
from backend.app.security.middleware import RateLimitMiddleware, SecurityHeadersMiddleware

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_directories()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Source-grounded Pakistani legal information API",
    version="1.0.0",
    docs_url="/api/docs" if settings.app_env != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.app_rate_limit_per_minute)
app.add_middleware(SecurityHeadersMiddleware)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, _exc: RequestValidationError):
    return JSONResponse({"detail": "The request was malformed or exceeded allowed limits."}, status_code=422)


@app.exception_handler(Exception)
async def unhandled_error(_request: Request, _exc: Exception):
    return JSONResponse({"detail": "The service could not complete the request."}, status_code=500)


frontend = Path(__file__).resolve().parents[2] / "frontend"
if frontend.exists():
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")
    app.mount(
        "/frontend/assets",
        StaticFiles(directory=frontend / "assets"),
        name="frontend-assets",
    )

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(frontend / "index.html")
