import json
import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class SettingsPathTests(SimpleTestCase):
    def configured_settings(self, url, cwd, media_root=None):
        environment = os.environ.copy()
        environment.update(DATABASE_URL=url, DJANGO_DEBUG="True", PYTHONPATH=str(settings.BASE_DIR))
        if media_root is not None:
            environment["DJANGO_MEDIA_ROOT"] = str(media_root)
        result = subprocess.run(
            [sys.executable, "-c", "import json; from config.settings import DATABASES, MEDIA_ROOT; print(json.dumps({'database': DATABASES['default'], 'media_root': str(MEDIA_ROOT)}))"],
            cwd=cwd, env=environment, capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

    def configured_database(self, url, cwd):
        return self.configured_settings(url, cwd)["database"]

    def test_relative_sqlite_uses_backend_database_from_either_launch_directory(self):
        for cwd in (settings.BASE_DIR, settings.BASE_DIR.parent):
            with self.subTest(cwd=cwd):
                database = self.configured_database("sqlite:///db.sqlite3", cwd)
                self.assertEqual(Path(database["NAME"]), settings.BASE_DIR / "db.sqlite3")

    def test_memory_database_is_preserved(self):
        self.assertEqual(self.configured_database("sqlite:///:memory:", settings.BASE_DIR)["NAME"], ":memory:")

    def test_absolute_sqlite_database_is_preserved(self):
        path = settings.BASE_DIR.parent / "custom.sqlite3"
        database = self.configured_database("sqlite:///" + path.as_posix(), settings.BASE_DIR)
        self.assertEqual(Path(database["NAME"]), path)

    def test_external_database_name_is_preserved(self):
        database = self.configured_database("postgresql://user:password@localhost/catalog", settings.BASE_DIR)
        self.assertEqual(database["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(database["NAME"], "catalog")

    def test_relative_media_root_uses_backend_directory_from_either_launch_directory(self):
        for cwd in (settings.BASE_DIR, settings.BASE_DIR.parent):
            with self.subTest(cwd=cwd):
                configured = self.configured_settings("sqlite:///:memory:", cwd, "./media")
                self.assertEqual(Path(configured["media_root"]), settings.BASE_DIR / "media")

    def test_absolute_media_root_is_preserved(self):
        path = settings.BASE_DIR.parent / "custom-media"
        configured = self.configured_settings("sqlite:///:memory:", settings.BASE_DIR, path)
        self.assertEqual(Path(configured["media_root"]), path)
