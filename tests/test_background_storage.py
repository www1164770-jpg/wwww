import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.background_image_service import ProcessedBackground
from backend.background_storage import (
    BackgroundFileNotFound,
    BackgroundStorageError,
    InvalidStoragePath,
    delete_background_file,
    read_background_file,
    resolve_background_path,
    store_processed_background,
)


def processed(content=b"webp-bytes"):
    return ProcessedBackground(content, 12, 8, "image/webp", len(content))


class BackgroundStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "uploads"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_stores_reads_and_deletes_uuid_webp_at_a_relative_path(self):
        storage_path = store_processed_background(processed(), 12, self.root)

        self.assertRegex(storage_path, r"^12/[0-9a-f-]{36}\.webp$")
        self.assertNotIn("\\", storage_path)
        self.assertEqual(read_background_file(self.root, storage_path), b"webp-bytes")
        self.assertTrue(delete_background_file(self.root, storage_path))
        self.assertFalse((self.root / storage_path).exists())

    def test_creates_only_the_positive_user_directory(self):
        storage_path = store_processed_background(processed(), 7, self.root)

        self.assertEqual(Path(storage_path).parent, Path("7"))
        self.assertEqual([entry.name for entry in self.root.iterdir()], ["7"])

    def test_rejects_invalid_processed_input_before_creating_root(self):
        invalid_values = (
            (processed(), True),
            (processed(), 0),
            (object(), 1),
            (ProcessedBackground("x", 1, 1, "image/webp", 1), 1),
            (ProcessedBackground(b"", 1, 1, "image/webp", 0), 1),
            (ProcessedBackground(b"x", 0, 1, "image/webp", 1), 1),
            (ProcessedBackground(b"x", True, 1, "image/webp", 1), 1),
            (ProcessedBackground(b"x", 1, 1, "image/png", 1), 1),
            (ProcessedBackground(b"x", 1, 1, "image/webp", True), 1),
            (ProcessedBackground(b"x", 1, 1, "image/webp", 2), 1),
        )

        for invalid_processed, user_id in invalid_values:
            with self.subTest(value=invalid_processed, user_id=user_id):
                with self.assertRaises(ValueError):
                    store_processed_background(invalid_processed, user_id, self.root)
                self.assertFalse(self.root.exists())

    def test_rejects_absolute_traversal_and_out_of_root_paths(self):
        for storage_path in ("/etc/passwd", "../outside.webp", "12/../../outside.webp", "C:/outside.webp"):
            with self.subTest(storage_path=storage_path):
                with self.assertRaises(InvalidStoragePath):
                    resolve_background_path(self.root, storage_path)

    def test_rejects_root_self_and_drive_relative_paths(self):
        for storage_path in (".", "C:relative.webp"):
            with self.subTest(storage_path=storage_path):
                with self.assertRaises(InvalidStoragePath):
                    resolve_background_path(self.root, storage_path)

    def test_rejects_existing_symlink_that_resolves_outside_root(self):
        resolved_root = self.root.resolve()
        linked_path = resolved_root / "linked.webp"
        outside_path = Path(self.temporary_directory.name) / "outside.webp"

        def resolve_path(path):
            return outside_path if path == linked_path else resolved_root

        with patch("backend.background_storage.Path.resolve", autospec=True, side_effect=resolve_path):
            with self.assertRaises(InvalidStoragePath):
                resolve_background_path(self.root, "linked.webp")

    def test_missing_read_raises_and_missing_delete_is_idempotent(self):
        with self.assertRaises(BackgroundFileNotFound) as raised:
            read_background_file(self.root, "12/missing.webp")

        self.assertNotIn(str(self.root), str(raised.exception))
        self.assertFalse(delete_background_file(self.root, "12/missing.webp"))

    def test_wraps_filesystem_errors_and_cleans_temporary_file_on_write_failure(self):
        with patch("backend.background_storage.Path.write_bytes", side_effect=OSError("write failed")):
            with self.assertRaises(BackgroundStorageError) as raised:
                store_processed_background(processed(), 4, self.root)

        self.assertNotIn(str(self.root), str(raised.exception))
        self.assertEqual(list((self.root / "4").iterdir()), [])

    def test_cleans_temporary_file_on_replace_failure(self):
        with patch("backend.background_storage.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaises(BackgroundStorageError):
                store_processed_background(processed(), 4, self.root)

        self.assertEqual(list((self.root / "4").iterdir()), [])

    def test_surfaces_cleanup_failure_after_a_write_failure(self):
        with patch("backend.background_storage.Path.write_bytes", side_effect=OSError("write failed")):
            with patch("backend.background_storage.Path.unlink", side_effect=OSError("cleanup failed")):
                with self.assertRaisesRegex(
                    BackgroundStorageError, "^Unable to clean up failed background storage$"
                ) as raised:
                    store_processed_background(processed(), 4, self.root)

        self.assertNotIn(str(self.root), str(raised.exception))

    def test_wraps_read_and_delete_filesystem_errors(self):
        storage_path = store_processed_background(processed(), 4, self.root)

        with patch("backend.background_storage.Path.read_bytes", side_effect=OSError("read failed")):
            with self.assertRaises(BackgroundStorageError) as read_error:
                read_background_file(self.root, storage_path)
        self.assertNotIn(str(self.root), str(read_error.exception))

        with patch("backend.background_storage.Path.unlink", side_effect=OSError("delete failed")):
            with self.assertRaises(BackgroundStorageError) as delete_error:
                delete_background_file(self.root, storage_path)
        self.assertNotIn(str(self.root), str(delete_error.exception))

    def test_delete_returns_false_when_file_disappears_before_unlink(self):
        storage_path = store_processed_background(processed(), 4, self.root)

        with patch("backend.background_storage.Path.unlink", side_effect=FileNotFoundError):
            self.assertFalse(delete_background_file(self.root, storage_path))

    def test_delete_returns_false_when_file_disappears_before_is_file(self):
        storage_path = store_processed_background(processed(), 4, self.root)

        with patch("backend.background_storage.Path.exists", side_effect=(True, False)):
            with patch("backend.background_storage.Path.is_file", return_value=False):
                self.assertFalse(delete_background_file(self.root, storage_path))

    def test_storage_source_does_not_process_images_or_import_pillow(self):
        source = Path(__file__).parents[1] / "backend" / "background_storage.py"
        contents = source.read_text(encoding="utf-8").lower()

        self.assertNotIn("pil", contents)
        self.assertNotIn("pillow", contents)
        self.assertNotIn("image.open", contents)


if __name__ == "__main__":
    unittest.main()
