import logging
import time

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import appointments, assistant, auth, health, invoices, knowledge, owners, pets, triage
from app.config import get_settings
from app.logging_config import configure_logging

configure_logging()
logger = logging.getLogger("app.request")

settings = get_settings()

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # The exception_handler below already logged the full traceback and
        # returned a response - Starlette's BaseHTTPMiddleware re-raises the
        # original exception here anyway once that response has been sent, so
        # this is just a duration breadcrumb, not a second incident to log.
        duration_ms = (time.perf_counter() - start) * 1000
        logger.warning(
            "%s %s -> 500 after %.1fms (see unhandled error above)",
            request.method, request.url.path, duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1fms)", request.method, request.url.path, response.status_code, duration_ms
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for anything a route/AI call didn't handle itself (DB drops,
    unexpected None, etc). Without this, Starlette's default 500 handling can
    surface internals to the client; this logs the full trace server-side and
    sends back a generic message instead. Registering for `Exception` doesn't
    shadow `HTTPException` or validation-error responses - Starlette resolves
    handlers by walking the exception's MRO and picks the most specific match,
    so those keep using FastAPI's own handlers."""
    logger.exception("%s %s -> unhandled error", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Something went wrong on our end. Please try again."},
    )


app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(owners.router, prefix="/api/owners", tags=["owners"])
app.include_router(pets.router, prefix="/api/pets", tags=["pets"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["appointments"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(triage.router, prefix="/api/triage", tags=["triage"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["assistant"])
