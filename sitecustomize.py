from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DJANGO_DIR = ROOT_DIR / "backend" / "django_core"

if str(DJANGO_DIR) not in sys.path:
    sys.path.insert(0, str(DJANGO_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
