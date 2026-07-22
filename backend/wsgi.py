"""WSGI entry point without development-only startup work."""

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app


application = app

__all__ = ["app", "application"]
