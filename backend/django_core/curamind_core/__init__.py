from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.celery_worker.celery_app import app as celery_app  # noqa: E402

__all__ = ["celery_app"]
