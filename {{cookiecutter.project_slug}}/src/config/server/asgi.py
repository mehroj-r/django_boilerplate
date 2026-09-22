import os

from config.bootstrap import setup_paths

setup_paths()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

from django.core.asgi import get_asgi_application  # noqa: E402  (must follow setup_paths)

application = get_asgi_application()
