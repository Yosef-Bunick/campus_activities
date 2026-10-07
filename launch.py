#!/usr/bin/env python3
"""Launch the Campus Events dev servers (backend + frontend) and open the app.

Usage:  python launch.py [--no-browser]

Backend  -> http://localhost:8000  (uvicorn, auto-reload, health at /health)
Frontend -> http://localhost:5173  (Vite, hot reload)

Runs each server in its own console window (Windows) so you can stop them
individually. Prints a health check for both before opening the browser.
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
IS_WINDOWS = os.name == "nt"

APP_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"


def backend_python() -> str:
    """Prefer the backend's venv python; fall back to whatever ran this script."""
    name = "python.exe" if IS_WINDOWS else "python"
    sub = "Scripts" if IS_WINDOWS else "bin"
    exe = BACKEND / ".venv" / sub / name
    return str(exe) if exe.exists() else sys.executable


def npm_cmd() -> str:
    return "npm.cmd" if IS_WINDOWS else "npm"


def run_detached(label, cwd, cmd):
    """Start cmd in its own console (Windows) or detached session (POSIX)."""
    print(f"[launch] {label}: {' '.join(cmd)}")
    kwargs = {}
    kwargs["cwd"] = str(cwd)
    if IS_WINDOWS:
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        return subprocess.Popen(cmd, **kwargs)
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        **kwargs,
    )


def wait_for(url, timeout=15.0) -> bool:
    """Poll url until it answers HTTP (any status) or timeout. Returns True/False."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    ap = argparse.ArgumentParser(description="Launch Campus Events dev servers")
    ap.add_argument("--no-browser", action="store_true", help="don't open the browser")
    args = ap.parse_args()

    if not (BACKEND / "dev.db").exists():
        print("[launch] backend/dev.db not found — one-time setup (run once):")
        print(f"  cd backend")
        print(f"  {backend_python()} -m alembic upgrade head")
        print(f"  {backend_python()} -m app.seed")
        print("[launch] continuing anyway (the backend will error if the schema is missing).\n")

    backend_proc = run_detached(
        "backend",
        BACKEND,
        [backend_python(), "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
    )
    frontend_proc = run_detached("frontend", FRONTEND, [npm_cmd(), "run", "dev"])

    print("\n[launch] checking that both servers come up (up to ~15s each)...")
    backend_ok = wait_for(BACKEND_URL + "/health")
    frontend_ok = wait_for(APP_URL)
    print(f"[launch] backend   {'OK' if backend_ok else 'NOT RESPONDING'}  {BACKEND_URL}")
    print(f"[launch] frontend  {'OK' if frontend_ok else 'NOT RESPONDING'}  {APP_URL}")

    if frontend_ok and not args.no_browser:
        webbrowser.open(APP_URL)
    elif not frontend_ok:
        print("[launch] frontend didn't come up — check its console window for errors.")

    print("\nCampus Events:")
    print(f"  app     {APP_URL}")
    print(f"  api     {BACKEND_URL}  (health: {BACKEND_URL}/health)")
    print("Stop by closing each server's console window.")
    print("Tip: set DEV_LOGIN=1 in backend/.env for the local 'sign in as' form (no Microsoft).")


if __name__ == "__main__":
    main()
