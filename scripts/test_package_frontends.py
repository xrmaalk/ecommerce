import os
import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from scripts import package_frontends as packager


class FrontendPackagingTests(unittest.TestCase):
    def make_distribution(self, root, name="dist", entry="new-build"):
        source = root / "frontend" / name
        (source / "assets").mkdir(parents=True)
        (source / "assets" / f"{entry}.js").write_text("export {};", encoding="utf-8")
        (source / "assets" / f"{entry}.css").write_text("body {}", encoding="utf-8")
        (source / ".htaccess").write_text("Options -Indexes\n", encoding="utf-8")
        (source / "index.html").write_text(
            f'<script type="module" src="/assets/{entry}.js"></script>'
            f'<link rel="stylesheet" href="/assets/{entry}.css">'
            '<script src="https://example.com/ad.js"></script>', encoding="utf-8",
        )
        return source

    def test_missing_entry_or_stylesheet_is_rejected(self):
        for extension in ("js", "css"):
            with self.subTest(extension=extension), tempfile.TemporaryDirectory() as directory:
                source = self.make_distribution(Path(directory))
                (source / "assets" / f"new-build.{extension}").unlink()
                with self.assertRaisesRegex(packager.PackagingError, "missing file"):
                    packager.distribution_files(source)

    def test_source_document_is_rejected(self):
        with self.assertRaisesRegex(packager.PackagingError, "built Vite entry"):
            packager.validate_index(b'<script type="module" src="/src/main.ts"></script>', {"src/main.ts"}, "source")

    def test_zip_uses_generated_index_bytes_and_build_timestamp_with_index_last(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_distribution(root)
            built_at = datetime(2026, 9, 30, 12, 34, 56)
            os.utime(source / "index.html", (built_at.timestamp(), built_at.timestamp()))
            temporary = packager.prepare_archive(source, root / "dist.zip", packager.distribution_files(source))
            with zipfile.ZipFile(temporary) as archive:
                self.assertEqual(archive.read("index.html"), (source / "index.html").read_bytes())
                self.assertEqual(archive.read(".htaccess"), (source / ".htaccess").read_bytes())
                self.assertEqual(archive.getinfo("index.html").date_time, (2026, 9, 30, 12, 34, 56))
                self.assertEqual(archive.namelist()[-1], "index.html")

    def test_every_run_builds_and_legacy_skip_flag_cannot_package_stale_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for distribution in packager.DISTRIBUTIONS:
                (root / distribution.archive_name).write_bytes(b"old archive")
            def build(repository):
                for distribution in packager.DISTRIBUTIONS:
                    self.make_distribution(repository, distribution.source_name, "fresh-from-build")
            with patch.object(packager, "repository_root", return_value=root), patch.object(packager, "run_frontend_build", side_effect=build) as rebuild, patch("sys.argv", ["package_frontends.py", "--skip-build"]):
                self.assertEqual(packager.main(), 0)
                rebuild.assert_called_once_with(root)
            for distribution in packager.DISTRIBUTIONS:
                with zipfile.ZipFile(root / distribution.archive_name) as archive:
                    self.assertIn(b"fresh-from-build.js", archive.read("index.html"))

    def test_build_failure_preserves_existing_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for distribution in packager.DISTRIBUTIONS:
                (root / distribution.archive_name).write_bytes(b"old archive")
            with patch.object(packager, "repository_root", return_value=root), patch.object(packager, "run_frontend_build", side_effect=packager.PackagingError("Build failed")), patch("sys.argv", ["package_frontends.py"]):
                self.assertEqual(packager.main(), 1)
            for distribution in packager.DISTRIBUTIONS:
                self.assertEqual((root / distribution.archive_name).read_bytes(), b"old archive")

    def test_invalid_second_distribution_preserves_both_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for distribution in packager.DISTRIBUTIONS:
                (root / distribution.archive_name).write_bytes(b"old archive")
                source = self.make_distribution(root, distribution.source_name)
            (source / "assets" / "new-build.js").unlink()
            with patch.object(packager, "repository_root", return_value=root), patch.object(packager, "run_frontend_build"), patch("sys.argv", ["package_frontends.py"]):
                self.assertEqual(packager.main(), 1)
            for distribution in packager.DISTRIBUTIONS:
                self.assertEqual((root / distribution.archive_name).read_bytes(), b"old archive")
            self.assertEqual(list(root.glob(".*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
