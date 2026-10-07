import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.csrf import CSRFMiddleware
from app.routers import (
    alerts,
    auth,
    dev_auth,
    events,
    favorites,
    health,
    hidden,
    microsoft_auth,
    moderation,
    users,
)

if settings.sentry_dsn:
    import sentry_sdk

    # Off unless SENTRY_DSN is set. No personal data: no IPs, cookies or bodies.
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1, send_default_pii=False)



@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = None
    if settings.worker_enabled:
        from app.worker import daily_loop

        task = asyncio.create_task(daily_loop())
    yield
    if task:
        task.cancel()


app = FastAPI(title="Campus Events API", version="0.1.0", lifespan=lifespan)

# Innermost: compresses route responses only (a month of events is ~100 KB of
# JSON, ~10x smaller gzipped); CSRF and CORS wrap it unchanged. Small bodies
# aren't worth it.
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Added before CORS so CORS is the outer layer: CSRF 403s still carry CORS headers.
app.add_middleware(CSRFMiddleware)

# The frontend (Vercel) and API (Render) are different origins. Credentials are
# allowed so the session cookie is sent.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(events.router)
app.include_router(dev_auth.router)
app.include_router(favorites.router)
app.include_router(hidden.router)
app.include_router(alerts.router)
app.include_router(microsoft_auth.router)
app.include_router(moderation.router)
