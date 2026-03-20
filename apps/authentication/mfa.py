from __future__ import annotations

import os
import uuid
from typing import Any

import pyotp
from django.core.cache import cache

from apps.authentication.models import User

MFA_ISSUER = os.getenv("MFA_ISSUER", "CuraMind AI")
MFA_CHALLENGE_TTL = int(os.getenv("MFA_CHALLENGE_TTL", "300"))


def normalize_mfa_code(code: str) -> str:
    return "".join(ch for ch in code if ch.isdigit())


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def get_totp(secret: str) -> pyotp.TOTP:
    return pyotp.TOTP(secret)


def build_mfa_provisioning_uri(user: User, secret: str) -> str:
    return get_totp(secret).provisioning_uri(name=user.email, issuer_name=MFA_ISSUER)


def verify_mfa_code(user: User, code: str) -> bool:
    if not user.mfa_secret:
        return False
    normalized = normalize_mfa_code(code)
    if len(normalized) != 6:
        return False
    return bool(get_totp(user.mfa_secret).verify(normalized, valid_window=1))


def _challenge_cache_key(token: str) -> str:
    return f"mfa_login_challenge:{token}"


def create_login_challenge(user: User, ip_address: str | None = None) -> str:
    token = str(uuid.uuid4())
    cache.set(
        _challenge_cache_key(token),
        {"user_id": str(user.id), "ip_address": ip_address or ""},
        timeout=MFA_CHALLENGE_TTL,
    )
    return token


def get_login_challenge(token: str) -> dict[str, Any] | None:
    challenge = cache.get(_challenge_cache_key(token))
    if not isinstance(challenge, dict):
        return None
    return challenge


def consume_login_challenge(token: str) -> dict[str, Any] | None:
    key = _challenge_cache_key(token)
    challenge = get_login_challenge(token)
    if challenge:
        cache.delete(key)
    return challenge
