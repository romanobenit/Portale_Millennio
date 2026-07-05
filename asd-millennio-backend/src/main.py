from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from core.celery_app import celery_app as _celery_app  # noqa: F401 — registra i task
from core.config import get_settings
from core.logger import setup_logging, logger
from core.rate_limit import limiter
from core.redis import close_redis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    from core.startup_checks import validate_production_config
    validate_production_config()
    logger.info("ASD Millennio backend avviato — ambiente: %s", settings.node_env)
    yield
    await close_redis()
    logger.info("Backend in shutdown")


app = FastAPI(
    title="ASD Millennio API",
    description="Piattaforma digitale ASD Millennio — MVP",
    version="1.0.0",
    docs_url="/docs" if settings.node_env != "production" else None,
    redoc_url="/redoc" if settings.node_env != "production" else None,
    lifespan=lifespan,
)

# ─── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# In produzione solo l'origine del dominio ufficiale.
# In sviluppo/staging aggiungiamo localhost per i dev tool.
_allowed_origins = [settings.app_url]
if settings.node_env != "production":
    _allowed_origins += [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3100",
        "http://localhost:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "stripe-signature"],
)


# ─── Exception handler globale ────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Errore non gestito: %s %s — %s", request.method, request.url, exc)
    return JSONResponse(
        status_code=500,
        content={"error": "ERRORE_INTERNO", "message": "Errore interno del server", "details": {}},
    )


# ─── Routers ──────────────────────────────────────────────────────────────────
from modules.soci.router import router as soci_router
from modules.soci.tessere_router import router as tessere_router
from modules.calendario.router import router as calendario_router
from modules.nft.router import router as nft_router
from modules.dirigenza.router import router as dirigenza_router
from modules.campi.router import router as campi_router
from modules.dirigenza.campi_router import router as dirigenza_campi_router
from modules.webhooks.stripe_handler import router as webhook_router

PREFIX = "/api/v1"

app.include_router(soci_router, prefix=PREFIX)
app.include_router(tessere_router, prefix=PREFIX)
app.include_router(calendario_router, prefix=PREFIX)
app.include_router(nft_router, prefix=PREFIX)
app.include_router(dirigenza_router, prefix=PREFIX)
app.include_router(campi_router, prefix=PREFIX)
app.include_router(dirigenza_campi_router, prefix=PREFIX)
app.include_router(webhook_router, prefix=PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.node_env}
