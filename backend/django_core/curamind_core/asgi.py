"""ASGI config for CuraMind AI."""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "curamind_core.settings")

from django.core.asgi import get_asgi_application  # noqa: E402

application = get_asgi_application()
