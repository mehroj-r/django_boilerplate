import keyword
import re
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, CommandError

LOCAL_APPS_MARKER = "LOCAL_APPS = ["
URLPATTERNS_MARKER = "urlpatterns = ["
# Present in api/v<n>/urls.py only when the project uses django-modern-rest,
# whose controllers are registered on a Router instead of a urlpatterns list.
ROUTER_MARKER = "router.include("


def camelize(app_name: str) -> str:
    """my_app -> MyApp (str.capitalize would give My_app)."""
    return "".join(part.title() for part in app_name.split("_") if part)


class Command(BaseCommand):
    help = "Create versioned API app with project structure"

    def add_arguments(self, parser):
        parser.add_argument("app_name", type=str, help="Name of the new app")
        parser.add_argument(
            "--ver",
            type=str,
            default="v1",
            help="API version folder to generate (default: v1)",
        )

    def handle(self, *args, **options):
        app_name = options["app_name"]
        version = options["ver"]

        self.validate_app_name(app_name)
        self.validate_version(version)

        base_dir = Path(settings.BASE_DIR)
        api_root = base_dir / "api" / version / app_name
        app_root = base_dir / "apps" / app_name

        for existing in (api_root, app_root):
            if existing.exists():
                raise CommandError(f"Path already exists, refusing to overwrite: {existing}")

        # -----------------------------------------------------
        # 1. Create API structure
        # -----------------------------------------------------
        self.create_files(
            api_root,
            {
                "__init__.py": "",
                "serializers.py": "",
                "views.py": "",
                "urls.py": self.build_app_urls(app_name),
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Created API module: {api_root}"))

        # -----------------------------------------------------
        # 2. Create App structure
        # -----------------------------------------------------
        self.create_files(
            app_root,
            {
                "__init__.py": "",
                "models.py": "",
                "apps.py": (
                    "from django.apps import AppConfig\n\n\n"
                    f"class {camelize(app_name)}Config(AppConfig):\n"
                    '    default_auto_field = "django.db.models.BigAutoField"\n'
                    f'    name = "{app_name}"\n'
                ),
                "admin.py": (
                    '"""Admin registrations for this app.\n\n'
                    "Use core.admin.BaseModelAdmin (or BaseSoftDeleteModelAdmin for soft-delete models).\n"
                    '"""\n'
                ),
                "tests.py": (
                    "from django.test import TestCase\n\n\n"
                    f"class {camelize(app_name)}Tests(TestCase):\n"
                    "    def test_placeholder(self):\n"
                    "        self.assertTrue(True)\n"
                ),
                "migrations/__init__.py": "",
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Created Django app: {app_root}"))

        # -----------------------------------------------------
        # 3. Register the app and route its URLs
        # -----------------------------------------------------
        self.add_to_local_apps(self.get_settings_file(), app_name)
        self.add_to_api_urls(base_dir / "api" / version / "urls.py", app_name, version)

        self.stdout.write(self.style.SUCCESS("App generation complete!"))
        self.stdout.write(f"Next: define models in apps/{app_name}/models.py, then `just makemigrations {app_name}`.")

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    @staticmethod
    def validate_app_name(app_name: str) -> None:
        if not app_name.isidentifier() or keyword.iskeyword(app_name):
            raise CommandError(f"'{app_name}' is not a valid Python module name.")
        if app_name != app_name.lower():
            raise CommandError("App names must be lowercase.")
        if app_name in settings.INSTALLED_APPS:
            raise CommandError(f"'{app_name}' is already in INSTALLED_APPS.")

    @staticmethod
    def validate_version(version: str) -> None:
        if not re.fullmatch(r"v\d+", version):
            raise CommandError(f"--ver must look like 'v1', got '{version}'.")

    # ---------------------------------------------------------
    # Utility Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _write_file(path: Path, content: str = "") -> None:
        """Write file and ensure folders exist."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def create_files(self, base_path: Path, files: dict) -> None:
        """Create multiple files under a base directory."""
        for relative_path, content in files.items():
            self._write_file(base_path / relative_path, content)

    @staticmethod
    def get_settings_file() -> Path:
        """Resolve settings/base.py regardless of which settings module is active."""
        module = settings.SETTINGS_MODULE  # e.g. "config.settings.dev"
        package = module.rsplit(".", 1)[0]  # -> "config.settings"
        return Path(settings.BASE_DIR).joinpath(*package.split("."), "base.py")

    def _insert_into_list(self, path: Path, marker: str, entry: str, label: str) -> None:
        """Insert `entry` just before the closing bracket of the list opened by `marker`."""
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

        start = next((i for i, line in enumerate(lines) if line.lstrip().startswith(marker)), None)
        if start is None:
            raise CommandError(f"'{marker}' not found in {path}")

        # Track bracket depth so a nested list cannot end the scan early.
        depth = 0
        end = None
        for i in range(start, len(lines)):
            depth += lines[i].count("[") - lines[i].count("]")
            if depth == 0:
                end = i
                break

        if end is None:
            raise CommandError(f"Could not find the end of '{marker}' in {path}")

        if any(entry.strip() in line for line in lines[start : end + 1]):
            self.stdout.write(self.style.WARNING(f"{label} already present in {path.name}"))
            return

        lines.insert(end, entry)
        path.write_text("".join(lines), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Registered {label} in {path.name}"))

    def add_to_local_apps(self, settings_file: Path, app_name: str) -> None:
        self._insert_into_list(settings_file, LOCAL_APPS_MARKER, f'    "{app_name}",\n', app_name)

    def uses_router(self) -> bool:
        """True when this project routes through dmr.routing.Router."""
        return ROUTER_MARKER in Path(settings.BASE_DIR).joinpath("api", "v1", "urls.py").read_text(encoding="utf-8")

    def build_app_urls(self, app_name: str) -> str:
        """urls.py for the new app, in whichever routing style the project uses."""
        if self.uses_router():
            return f'from dmr.routing import Router\n\napp_name = "{app_name}"\n\nrouter = Router("", [])\n'
        return f'app_name = "{app_name}"\n\nurlpatterns = []\n'

    def add_to_api_urls(self, urls_file: Path, app_name: str, version: str) -> None:
        if self.uses_router():
            self._register_router(urls_file, app_name, version)
            return

        entry = f'    path("{app_name}/", include("api.{version}.{app_name}.urls", namespace="{app_name}")),\n'
        self._insert_into_list(urls_file, URLPATTERNS_MARKER, entry, f"api.{version}.{app_name}.urls")

    def _register_router(self, urls_file: Path, app_name: str, version: str) -> None:
        """Add an import and a router.include() call to a dmr-style urls.py."""
        if not urls_file.exists():
            raise CommandError(f"File not found: {urls_file}")

        content = urls_file.read_text(encoding="utf-8")
        import_line = f"from api.{version}.{app_name} import urls as {app_name}_urls\n"
        include_line = f'router.include({app_name}_urls.router, namespace="{app_name}")\n'

        if include_line in content:
            self.stdout.write(self.style.WARNING(f"api.{version}.{app_name}.urls already present in {urls_file.name}"))
            return

        lines = content.splitlines(keepends=True)

        last_import = max(
            (i for i, line in enumerate(lines) if line.startswith(f"from api.{version}")),
            default=None,
        )
        last_include = max(
            (i for i, line in enumerate(lines) if line.startswith(ROUTER_MARKER)),
            default=None,
        )
        if last_import is None or last_include is None:
            raise CommandError(f"Could not find the router block in {urls_file}")

        # Insert the include first so the earlier import insert does not shift it.
        lines.insert(last_include + 1, include_line)
        lines.insert(last_import + 1, import_line)

        urls_file.write_text("".join(lines), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Registered api.{version}.{app_name}.urls in {urls_file.name}"))
