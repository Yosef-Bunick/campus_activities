from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import health

app = FastAPI(title="Campus Events API", version="0.1.0")

# The frontend (Vercel) and API (Render) are different origins. Credentials are
# allowed now so the Milestone 1 session cookie works without touching this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
