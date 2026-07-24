import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
CONFIG_MODULE = "background_config"


class BackgroundStorageConfigTests(unittest.TestCase):
    def _load_config(self, upload_root=None):
        previous = os.environ.pop("BACKGROUND_UPLOAD_ROOT", None)
        try:
            if upload_root is not None:
                os.environ["BACKGROUND_UPLOAD_ROOT"] = str(upload_root)
            sys.path.insert(0, str(BACKEND_DIR))
            sys.modules.pop(CONFIG_MODULE, None)
            return importlib.import_module(CONFIG_MODULE)
        finally:
            sys.path.remove(str(BACKEND_DIR))
            sys.modules.pop(CONFIG_MODULE, None)
            if previous is not None:
                os.environ["BACKGROUND_UPLOAD_ROOT"] = previous

    def test_dependency_contract_rejects_a_second_imaging_dependency(self):
        global ROOT_DIR

        with tempfile.TemporaryDirectory() as temporary_directory:
            fixture_root = Path(temporary_directory)
            (fixture_root / "requirements.txt").write_text(
                "Pillow==12.3.0\nopencv-contrib-python==4.11.0.86\n",
                encoding="utf-8",
            )
            original_root = ROOT_DIR
            ROOT_DIR = fixture_root
            try:
                with self.assertRaises(AssertionError):
                    self.test_dependency_is_the_only_pinned_pillow_declaration()
            finally:
                ROOT_DIR = original_root

    def test_dependency_is_the_only_pinned_pillow_declaration(self):
        dependency_lines = [
            line.strip()
            for line in (ROOT_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        dependency_names = [
            re.match(r"[A-Za-z0-9_.-]+", line).group(0).lower()
            for line in dependency_lines
        ]
        pillow_declarations = [
            line for line, name in zip(dependency_lines, dependency_names)
            if name == "pillow"
        ]
        imaging_library_names = {
            "pil", "pillow", "pillow-simd", "imageio", "opencv-python",
            "opencv-python-headless", "opencv-contrib-python", "scikit-image",
            "wand", "pyvips",
        }

        self.assertEqual(pillow_declarations, ["Pillow==12.3.0"])
        self.assertEqual(
            [name for name in dependency_names if name in imaging_library_names],
            ["pillow"],
        )

    def test_module_exposes_exact_immutable_upload_configuration(self):
        config = self._load_config()

        self.assertEqual(config.BACKGROUND_UPLOAD_FIELD, "file")
        self.assertEqual(config.BACKGROUND_MAX_FILE_BYTES, 10 * 1024 * 1024)
        self.assertEqual(config.BACKGROUND_MAX_REQUEST_BYTES, 11 * 1024 * 1024)
        self.assertEqual(config.BACKGROUND_MAX_PIXELS, 20_000_000)
        self.assertEqual(config.BACKGROUND_MAX_WIDTH, 2560)
        self.assertEqual(config.BACKGROUND_MAX_HEIGHT, 1440)
        self.assertEqual(config.BACKGROUND_WEBP_QUALITY, 84)
        self.assertIs(type(config.BACKGROUND_ALLOWED_IMAGE_FORMATS), frozenset)
        self.assertEqual(config.BACKGROUND_ALLOWED_IMAGE_FORMATS, frozenset({"JPEG", "PNG", "WEBP"}))
        self.assertEqual(config.BACKGROUND_OUTPUT_FORMAT, "WEBP")
        self.assertEqual(config.BACKGROUND_OUTPUT_MIME_TYPE, "image/webp")
        self.assertIsInstance(config.BACKGROUND_UPLOAD_ROOT, Path)

    def test_upload_root_defaults_from_module_directory_without_creating_it(self):
        expected_root = BACKEND_DIR / "uploads" / "backgrounds"
        self.assertFalse(expected_root.exists())

        config = self._load_config()

        self.assertEqual(config.BACKGROUND_UPLOAD_ROOT, expected_root)
        self.assertFalse(expected_root.exists())

    def test_upload_root_honors_environment_override_without_touching_disk(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            override_root = Path(temporary_directory) / "private-backgrounds"
            config = self._load_config(override_root)

            self.assertEqual(config.BACKGROUND_UPLOAD_ROOT, override_root)
            self.assertFalse(override_root.exists())

    def test_wsgi_import_publishes_upload_limits_without_upload_side_effects(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            upload_root = Path(temporary_directory) / "not-created"
            environment = os.environ.copy()
            environment.update(
                {
                    "BACKGROUND_UPLOAD_ROOT": str(upload_root),
                    "PYTHON_DOTENV_DISABLED": "1",
                    "REDIS_URL": "redis://127.0.0.1:1/0",
                    "APP_ENV": "development",
                    "FLASK_ENV": "development",
                    "PYTHONPATH": str(BACKEND_DIR),
                }
            )
            probe = """
import json
from pathlib import Path
from wsgi import app
import background_config
payload = {
    'max_content_length': app.config['MAX_CONTENT_LENGTH'],
    'file_limit': app.config['BACKGROUND_MAX_FILE_BYTES'],
    'upload_root': str(app.config['BACKGROUND_UPLOAD_ROOT']),
    'root_exists': Path(background_config.BACKGROUND_UPLOAD_ROOT).exists(),
}
print('BACKGROUND_CONFIG_PROBE=' + json.dumps(payload, sort_keys=True))
"""
            result = subprocess.run(
                [sys.executable, "-c", probe],
                cwd=BACKEND_DIR,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            line = next(
                line for line in result.stdout.splitlines()
                if line.startswith("BACKGROUND_CONFIG_PROBE=")
            )
            payload = json.loads(line.split("=", 1)[1])
            self.assertEqual(payload["max_content_length"], 11 * 1024 * 1024)
            self.assertEqual(payload["file_limit"], 10 * 1024 * 1024)
            self.assertEqual(payload["upload_root"], str(upload_root))
            self.assertFalse(payload["root_exists"])

    def test_gitignore_has_only_the_specific_background_upload_rule(self):
        rules = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual(rules.count("backend/uploads/backgrounds/"), 1)
        normalized_rules = [rule.strip().lower().replace("\\", "/") for rule in rules]
        forbidden_broad_rules = {
            "backend", "backend/", "uploads", "uploads/", "backend/uploads/",
            "migrations", "migrations/", "backend/migrations/", "tests", "tests/",
            "backend/tests/",
        }

        self.assertFalse(set(normalized_rules) & forbidden_broad_rules)
        self.assertFalse(
            any(
                re.fullmatch(
                    r"(?:\*\*/)?(?:backend|uploads|migrations|tests)/(?:\*|\*\*)/?",
                    rule,
                )
                for rule in normalized_rules
            )
        )
        self.assertFalse(
            any(
                rule.startswith("backend/uploads/")
                and rule != "backend/uploads/backgrounds/"
                for rule in normalized_rules
            )
        )
        self.assertFalse(any(".gitkeep" in rule for rule in normalized_rules))
        self.assertFalse(
            any(
                re.match(r"^[a-z]:/", rule) or rule.startswith("/")
                for rule in normalized_rules
            )
        )


if __name__ == "__main__":
    unittest.main()
