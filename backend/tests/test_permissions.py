from app.core.permissions import (
    PERMISSIONS,
    Role,
    can,
    limits_for,
    outranks,
    permissions_for,
)


def test_matrix_spot_checks():
    assert can(Role.STUDENT, "event.create.club")
    assert not can(Role.SECURITY, "event.create.club")
    assert not can(Role.STUDENT_GOV, "user.ban")  # SGA cannot ban
    assert can(Role.MANAGER, "user.ban")
    assert can(Role.SECURITY, "modlog.view")
    assert not can(Role.OWNER, "no.such.permission")  # unknown = denied


def test_owner_has_everything():
    assert permissions_for(Role.OWNER) == sorted(PERMISSIONS)


def test_hierarchy():
    assert outranks(Role.OWNER, Role.MANAGER)
    assert not outranks(Role.MANAGER, Role.MANAGER)  # not your peers
    assert not outranks(Role.MANAGER, Role.OWNER)


def test_limits():
    assert limits_for(Role.STUDENT)["max_days_ahead"] == 90
    assert limits_for(Role.STUDENT_GOV)["max_days_ahead"] == 365
    assert limits_for(Role.MANAGER)["max_events_created_per_day"] is None
