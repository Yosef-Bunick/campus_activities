from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core import database
from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["database"] == "connected"


def test_health_503_when_database_down(monkeypatch):
    class BrokenEngine:
        def connect(self, *a, **kw):
            raise OperationalError("SELECT 1", {}, Exception("down"))

    monkeypatch.setattr(database, "engine", BrokenEngine())
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["status"] == "degraded"


def test_cors_allows_frontend_origin():
    r = client.options(
        "/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
