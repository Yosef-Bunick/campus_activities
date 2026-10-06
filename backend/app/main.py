from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    users,
)

app = FastAPI(title="Campus Events API", version="0.1.0")

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
