"""Majors (ADR-028, ADR-032). The list itself lives in `backend/majors.txt`,
one per line, so adding a major is just adding a line: no code, no restart.

Each line's key is a slug of its text ("Computer Science" -> "computer_science").
Keys are what's stored on users and events, so renaming a line orphans the
old key (those people are asked to pick again); adding is always safe.
"""

from __future__ import annotations

import re
from pathlib import Path

MAJORS_FILE = Path(__file__).resolve().parents[2] / "majors.txt"
MAX_EVENT_MAJORS = 3  # an event can be tagged with at most this many majors

_cache: dict = {"mtime": None, "majors": {}}


def slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:40]


def majors() -> dict[str, str]:
    """{key: label}, in file order. Re-read when the file changes."""
    try:
        mtime = MAJORS_FILE.stat().st_mtime
    except FileNotFoundError:
        return {}
    if mtime != _cache["mtime"]:
        out: dict[str, str] = {}
        for raw in MAJORS_FILE.read_text(encoding="utf-8").splitlines():
            label = raw.strip()
            if label and not label.startswith("#") and slug(label):
                out.setdefault(slug(label), label[:80])
        _cache.update(mtime=mtime, majors=out)
    return _cache["majors"]


def is_major(key: str) -> bool:
    return key in majors()
