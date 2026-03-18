import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DJANGO_DIR = ROOT_DIR / "backend" / "django_core"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(DJANGO_DIR) not in sys.path:
    sys.path.insert(0, str(DJANGO_DIR))

os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "True")
