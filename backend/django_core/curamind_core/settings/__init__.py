"""Settings loader."""

import os

ENV = os.getenv("DJANGO_ENV", "dev").lower()

if ENV in {"prod", "production"}:
    from .prod import *  # noqa: F401,F403
else:
    from .dev import *  # noqa: F401,F403
