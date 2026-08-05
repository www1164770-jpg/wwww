from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR if (SCRIPT_DIR / "backend").is_dir() else SCRIPT_DIR.parent
APP_VIEW = PROJECT_ROOT / "backend" / "frontend" / "src" / "App.vue"
f = APP_VIEW.open("r", encoding="utf-8")
