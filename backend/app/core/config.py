"""Settings, read from environment variables (architecture §12).

Locally they come from the repo-root `.env` (copy `.env.example`). On Render
they are set in the dashboard. A real environment variable always wins over
`.env`, so nothing in the file can override production config.

Scheduling limits are NOT here: they live in `core/permissions.py`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


def _load_dotenv(path: Path) -> None:
    """Minimal KEY=value reader, so we don't need python-dotenv."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        # Drop trailing "   # comment" (the .env.example style) and quotes.
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def _resolve_sqlite(url: str) -> str:
    """Anchor a relative SQLite path to backend/, so uvicorn, alembic and
    pytest all hit the same file no matter which directory they run from.
    Also accepts the `postgres://` spelling some hosts (Neon, Heroku) hand out,
    which SQLAlchemy 2 rejects."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    prefix = "sqlite:///"
    if url.startswith(prefix) and not url.startswith(prefix + "/"):
        rel = url[len(prefix) :]
        if rel != ":memory:" and not Path(rel).is_absolute():
            return prefix + (BACKEND_DIR / rel).resolve().as_posix()
    return url


_load_dotenv(REPO_ROOT / ".env")

# Westchester Community College's Microsoft tenant (architecture §8). The
# default, so a missing env var can never lock every student out.
WCC_TENANT_ID = "4981a704-f6a3-4ac0-89c2-a3812354a3ff"


@dataclass(frozen=True)
class Settings:
    database_url: str = _resolve_sqlite(os.getenv("DATABASE_URL", "sqlite:///./dev.db"))
    ms_client_id: str = os.getenv("MS_CLIENT_ID", "")
    ms_client_secret: str = os.getenv("MS_CLIENT_SECRET", "")
    ms_redirect_uri: str = os.getenv(
        "MS_REDIRECT_URI", "http://localhost:8000/auth/microsoft/callback"
    )
    allowed_tenant_ids: tuple[str, ...] = tuple(
        t.strip()
        for t in os.getenv("ALLOWED_TENANT_IDS", WCC_TENANT_ID).split(",")
        if t.strip()
    )
    email_domain_requirement: str = os.getenv("EMAIL_DOMAIN_REQUIREMENT", "sunywcc.edu")
    owner_email: str = os.getenv("OWNER_EMAIL", "")
    session_secret: str = os.getenv("SESSION_SECRET", "")
    inactivity_delete_days: int = int(os.getenv("INACTIVITY_DELETE_DAYS", "150"))
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    sentry_dsn: str = os.getenv("SENTRY_DSN", "")
    # Daily jobs (150-day purge) inside the API process; tests turn it off.
    worker_enabled: bool = os.getenv("WORKER_ENABLED", "1") == "1"
    # Local-only "sign in as" for testing before/without Microsoft (ADR-023).
    dev_login_flag: bool = os.getenv("DEV_LOGIN", "") == "1"

    @property
    def dev_login(self) -> bool:
        """Never on an HTTPS (deployed) frontend, whatever the flag says."""
        return self.dev_login_flag and self.frontend_origin.startswith("http://localhost")


settings = Settings()
