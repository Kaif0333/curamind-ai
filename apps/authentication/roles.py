from __future__ import annotations

import os
from typing import cast

from apps.authentication.models import User


def get_self_assignable_roles() -> set[str]:
    allow_roles = os.getenv("ALLOW_SELF_ASSIGN_ROLES", "false").lower() == "true"
    if not allow_roles:
        return {cast(str, User.Role.PATIENT)}

    configured_roles = {
        role.strip()
        for role in os.getenv(
            "SELF_ASSIGNABLE_ROLES",
            ",".join(
                [
                    cast(str, User.Role.PATIENT),
                    cast(str, User.Role.DOCTOR),
                    cast(str, User.Role.RADIOLOGIST),
                    cast(str, User.Role.NURSE),
                ]
            ),
        ).split(",")
        if role.strip()
    }
    configured_roles.discard(cast(str, User.Role.ADMIN))
    return configured_roles or {cast(str, User.Role.PATIENT)}


def get_self_assignable_role_choices() -> list[tuple[str, str]]:
    allowed_roles = get_self_assignable_roles()
    return [(value, label) for value, label in User.Role.choices if value in allowed_roles]
