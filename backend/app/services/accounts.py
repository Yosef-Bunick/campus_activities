"""Who may sign in, and turning a verified Microsoft identity into a User.

The Microsoft router (Milestone 1, after the Entra keys exist) validates the ID
token, then calls `sign_in()` with its claims. Everything here is testable
without Microsoft.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.core.config import settings
from app.core.permissions import Role
from app.models.user import BannedAccount, User

REJECT_DOMAIN = "Only Westchester Community College accounts can use this app"
# Microsoft's tenant for personal accounts (outlook.com, hotmail, or any email
# registered as a Microsoft account). Microsoft verifies those emails.
MSA_CONSUMER_TENANT = "9188040d-6c67-4c5b-b112-36a304b66dad"
REJECT_BANNED = "This account has been banned"


class SignInRejected(Exception):
    pass


@dataclass(frozen=True)
class MicrosoftIdentity:
    tid: str
    oid: str
    email: str
    name: str = ""


def account_hash(tid: str, oid: str) -> str:
    return hashlib.sha256(f"{tid}:{oid}".encode()).hexdigest()


def email_domain_ok(email: str, required: str) -> bool:
    """Match on a dot: my.sunywcc.edu passes, fakesunywcc.edu doesn't."""
    domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
    required = required.lower().lstrip(".")
    return bool(domain) and (domain == required or domain.endswith("." + required))


def is_owner_email(email: str) -> bool:
    return bool(settings.owner_email) and email.lower() == settings.owner_email.lower()


def is_owner(ident: MicrosoftIdentity) -> bool:
    """OWNER_EMAIL, but only from a tenant whose email claim we can trust (ADR-029):
    WCC's own tenant or Microsoft's personal-account tenant. Any other tenant's
    admin could put any email on an account, so it never becomes owner."""
    trusted = ident.tid in settings.allowed_tenant_ids or ident.tid == MSA_CONSUMER_TENANT
    return trusted and is_owner_email(ident.email)


def gate(ident: MicrosoftIdentity) -> None:
    """WCC tenant AND school domain, or the owner's account (architecture §8)."""
    if is_owner(ident):
        return
    if ident.tid not in settings.allowed_tenant_ids:
        raise SignInRejected(REJECT_DOMAIN)
    if not email_domain_ok(ident.email, settings.email_domain_requirement):
        raise SignInRejected(REJECT_DOMAIN)


def is_banned(session: Session, tid: str, oid: str) -> bool:
    return session.get(BannedAccount, account_hash(tid, oid)) is not None


def sign_in(session: Session, ident: MicrosoftIdentity) -> User:
    gate(ident)
    if is_banned(session, ident.tid, ident.oid):
        raise SignInRejected(REJECT_BANNED)
    user = session.exec(
        select(User).where(User.ms_tenant_id == ident.tid, User.ms_object_id == ident.oid)
    ).first()
    if user is None:
        user = User(ms_tenant_id=ident.tid, ms_object_id=ident.oid, email=ident.email)
    user.email = ident.email
    user.display_name = ident.name or user.display_name
    # OWNER_EMAIL (from a trusted tenant) is the only way to become owner.
    if is_owner(ident):
        user.role = Role.OWNER.value
    elif user.role == Role.OWNER.value:
        user.role = Role.STUDENT.value  # OWNER_EMAIL changed: the old owner loses it
    user.last_active_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
