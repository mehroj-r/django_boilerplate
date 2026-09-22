import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase


class StartAppCommandTests(SimpleTestCase):
    app_name = "widget_shop"

    def setUp(self):
        self.base = Path(settings.BASE_DIR)
        self.api_root = self.base / "api" / "v1" / self.app_name
        self.app_root = self.base / "apps" / self.app_name
        self.settings_file = self.base / "config" / "settings" / "base.py"
        self.urls_file = self.base / "api" / "v1" / "urls.py"
        self.settings_backup = self.settings_file.read_text()
        self.urls_backup = self.urls_file.read_text()

    def tearDown(self):
        shutil.rmtree(self.api_root, ignore_errors=True)
        shutil.rmtree(self.app_root, ignore_errors=True)
        self.settings_file.write_text(self.settings_backup)
        self.urls_file.write_text(self.urls_backup)

    def test_scaffolds_both_trees(self):
        call_command("startapp", self.app_name)

        for expected in ("__init__.py", "models.py", "apps.py", "admin.py", "tests.py", "migrations/__init__.py"):
            self.assertTrue((self.app_root / expected).exists(), expected)
        for expected in ("__init__.py", "views.py", "serializers.py", "urls.py"):
            self.assertTrue((self.api_root / expected).exists(), expected)

    def test_config_class_is_camel_cased(self):
        call_command("startapp", self.app_name)

        # str.capitalize() would produce "Widget_shopConfig".
        self.assertIn("class WidgetShopConfig(AppConfig):", (self.app_root / "apps.py").read_text())

    def test_registers_the_app_and_routes_its_urls(self):
        call_command("startapp", self.app_name)

        self.assertIn(f'"{self.app_name}",', self.settings_file.read_text())
        # Without this the generated urls.py is orphaned and never served.
        # Matches both routing styles: DRF's include(...) and dmr's Router.
        self.assertIn(f"api.v1.{self.app_name}", self.urls_file.read_text())

    def test_rejects_invalid_names(self):
        for bad in ("class", "Widget", "widget-shop", "account"):
            with self.assertRaises(CommandError, msg=bad):
                call_command("startapp", bad)

    def test_rejects_a_bad_version(self):
        with self.assertRaises(CommandError):
            call_command("startapp", self.app_name, "--ver", "one")
