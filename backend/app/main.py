import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config.database import client, ensure_indexes
from app.config.logging import setup_logging
from app.config.settings import get_settings
from app.middleware.rate_limit import limiter
from app.routes.auth_routes import router as auth_router
from app.routes.chat_routes import router as chat_router
from app.routes.community_routes import router as community_router
from app.routes.connection_routes import router as connection_router
from app.routes.emotion_routes import router as emotion_router
from app.routes.feedback_routes import router as feedback_router
from app.routes.social_ws import router as social_ws_router
from app.routes.solo_routes import router as solo_router

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):  # noqa: ARG001
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):  # noqa: ARG001
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):  # noqa: ARG001
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.on_event("startup")
async def startup_event() -> None:
    await ensure_indexes()
    logger.info("Indexes initialized")
    try:
        from app.services.community_feed_service import community_feed_service

        await community_feed_service.seed_if_empty()
        logger.info("Community feed seeded")
    except Exception:  # noqa: BLE001
        logger.exception("Community feed seed failed")
    if settings.app_env.lower() == "production" and len(settings.jwt_secret_key) < 32:
        logger.warning(
            "APP_ENV=production but JWT_SECRET_KEY is shorter than 32 characters; use a long random secret.",
        )


@app.get("/health", response_model=None)
async def health(ready: bool = False):
    """Liveness: always 200 when the process is up. Set ready=1 to verify MongoDB (for orchestrators)."""
    body: dict = {"status": "ok", "service": settings.app_name}
    if not ready:
        return body
    try:
        await client.admin.command("ping")
        body["mongodb"] = "ok"
        return body
    except Exception as exc:  # noqa: BLE001
        logger.exception("Readiness check failed: %s", exc)
        body["mongodb"] = "error"
        return JSONResponse(status_code=503, content=body)


app.include_router(auth_router)
app.include_router(emotion_router)
app.include_router(chat_router)
app.include_router(community_router)
app.include_router(connection_router)
app.include_router(feedback_router)
app.include_router(social_ws_router)
app.include_router(solo_router)
