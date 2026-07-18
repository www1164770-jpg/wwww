from pathlib import Path
import sys

from flask_apscheduler import APScheduler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"

for import_root in (PROJECT_ROOT, BACKEND_ROOT):
    import_path = str(import_root)
    if import_path not in sys.path:
        sys.path.insert(0, import_path)


def _import_flask_app():
    """Import the Flask app without starting a serverless background scheduler."""
    original_scheduler_start = APScheduler.start
    APScheduler.start = lambda self, *args, **kwargs: None
    try:
        from backend.app import app as flask_app
    finally:
        APScheduler.start = original_scheduler_start
    return flask_app


app = _import_flask_app()

__all__ = ["app"]
