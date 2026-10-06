"""Roles, permissions AND scheduling limits. THE file to edit (architecture §5).

The backend checks these on every write. GET /auth/me sends them to the
frontend, which only uses them to show or hide buttons. Never trust the client.
"""

from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    MANAGER = "manager"
    STUDENT_GOV = "student_gov"
    SECURITY = "security"
    STUDENT = "student"


ROLE_RANK = {
    Role.OWNER: 100,
    Role.MANAGER: 80,
    Role.STUDENT_GOV: 60,
    Role.SECURITY: 40,
    Role.STUDENT: 20,
}

ALL = set(Role)
PERMISSIONS: dict[str, set[Role]] = {
    "event.view":            ALL,
    "event.create.friend":   ALL,
    "event.create.club":     ALL - {Role.SECURITY},
    "event.create.main":     {Role.OWNER, Role.MANAGER, Role.STUDENT_GOV},
    "event.edit_any":        {Role.OWNER},
    "event.cancel_any":      {Role.OWNER, Role.MANAGER, Role.STUDENT_GOV},
    "event.approve_overlap": {Role.OWNER, Role.STUDENT_GOV},
    "user.ban":              {Role.OWNER, Role.MANAGER},
    "user.change_role":      {Role.OWNER, Role.MANAGER},
    "map.manage":            {Role.OWNER, Role.MANAGER},
    "modlog.view":           {Role.OWNER, Role.MANAGER, Role.SECURITY},
}  # fmt: skip

# ── Scheduling limits ──
MAX_DAYS_AHEAD = {            # how far ahead you can schedule (single or recurring)
    Role.OWNER: 365, Role.MANAGER: 365, Role.STUDENT_GOV: 365,
    Role.SECURITY: 90, Role.STUDENT: 90,
}  # fmt: skip
CAN_DOUBLE_BOOK_SELF = {Role.OWNER, Role.MANAGER, Role.STUDENT_GOV}  # others: 1 event at a time
ROOM_MAX_OVERLAPPING = 2      # default; a Room can override it (e.g. the cafeteria)
MAX_EVENTS_CREATED_PER_DAY = {Role.STUDENT: 10, Role.SECURITY: 10}   # anti-spam; others unlimited

# ── Automatic abuse flags (Phase 2): alert managers + owner, never auto-ban ──
FLAG_REPORTS_PER_EVENT = 3        # this many reports on one event
FLAG_CAP_HITS_PER_WEEK = 3        # hit the daily creation cap this many times in 7 days
FLAG_ROOM_FULL_PER_WEEK = 5       # sent this many events to room approval in 7 days


def can(role: Role, perm: str) -> bool:
    """Unknown permission names are denied, never allowed."""
    return Role(role) in PERMISSIONS.get(perm, set())


def outranks(actor: Role, target: Role) -> bool:
    """Hierarchy rule: you can only act on users below you, and only assign
    roles below your own. So only the owner can create managers."""
    return ROLE_RANK[Role(actor)] > ROLE_RANK[Role(target)]


def permissions_for(role: Role) -> list[str]:
    return sorted(p for p, roles in PERMISSIONS.items() if Role(role) in roles)


def limits_for(role: Role) -> dict:
    role = Role(role)
    return {
        "max_days_ahead": MAX_DAYS_AHEAD[role],
        "can_double_book_self": role in CAN_DOUBLE_BOOK_SELF,
        "room_max_overlapping": ROOM_MAX_OVERLAPPING,
        "max_events_created_per_day": MAX_EVENTS_CREATED_PER_DAY.get(role),  # None = unlimited
    }
