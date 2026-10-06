"""Majors people can pick, and events can be tagged with (ADR-028). THE file to edit.

PLACEHOLDER LIST: replace with WCC's real program list. Keep the keys short and
stable (they're stored on users and events); the labels can change freely.
"""

MAJORS: dict[str, str] = {
    "undeclared": "Undeclared",
    "business": "Business",
    "computer_science": "Computer Science",
    "engineering": "Engineering",
    "health_sciences": "Health Sciences",
    "liberal_arts": "Liberal Arts",
    "nursing": "Nursing",
    "visual_arts": "Visual Arts",
}

MAX_EVENT_MAJORS = 3  # an event can be tagged with at most this many majors


def is_major(key: str) -> bool:
    return key in MAJORS
