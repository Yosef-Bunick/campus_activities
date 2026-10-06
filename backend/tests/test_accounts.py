import pytest
from tests.conftest import WCC

from app.services.accounts import (
    MicrosoftIdentity,
    SignInRejected,
    account_hash,
    email_domain_ok,
    sign_in,
)
from app.models.user import BannedAccount


@pytest.mark.parametrize(
    ("email", "ok"),
    [
        ("a@sunywcc.edu", True),
        ("a@my.sunywcc.edu", True),
        ("a@MY.SUNYWCC.EDU", True),
        ("a@fakesunywcc.edu", False),
        ("a@sunywcc.edu.evil.com", False),
        ("a@gmail.com", False),
        ("not-an-email", False),
    ],
)
def test_domain_matches_on_a_dot(email, ok):
    assert email_domain_ok(email, "sunywcc.edu") is ok


def test_student_signs_in_as_student(db):
    user = sign_in(db, MicrosoftIdentity(WCC, "o1", "a@my.sunywcc.edu", "A"))
    assert user.role == "student"


def test_same_tid_oid_is_same_user_even_if_email_changes(db):
    u1 = sign_in(db, MicrosoftIdentity(WCC, "o1", "a@my.sunywcc.edu"))
    u2 = sign_in(db, MicrosoftIdentity(WCC, "o1", "renamed@my.sunywcc.edu"))
    assert u1.id == u2.id and u2.email == "renamed@my.sunywcc.edu"


def test_school_email_from_another_tenant_is_rejected(db):
    with pytest.raises(SignInRejected):
        sign_in(db, MicrosoftIdentity("other-tenant", "o1", "a@my.sunywcc.edu"))


def test_wcc_tenant_with_wrong_domain_is_rejected(db):
    with pytest.raises(SignInRejected):
        sign_in(db, MicrosoftIdentity(WCC, "o1", "a@fakesunywcc.edu"))


def test_owner_email_is_exempt_and_becomes_owner(db):
    user = sign_in(db, MicrosoftIdentity("personal-msa-tenant", "o9", "Owner@Gmail.com"))
    assert user.role == "owner"


def test_banned_account_cannot_sign_in(db):
    db.add(BannedAccount(account_sha256=account_hash(WCC, "o1")))
    db.commit()
    with pytest.raises(SignInRejected):
        sign_in(db, MicrosoftIdentity(WCC, "o1", "a@my.sunywcc.edu"))
