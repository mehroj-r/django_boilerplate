"""Interpreter bootstrap shared by every entrypoint.

Django apps live in ``src/apps/`` but are declared in ``INSTALLED_APPS`` by their
bare label (``"account"``), so ``src/apps`` has to be importable before
``django.setup()`` runs.

Every process that boots Django -- ``manage.py``, ``asgi.py`` and ``wsgi.py`` --
must call :func:`setup_paths` first. Forgetting it in a server entrypoint fails
with ``ModuleNotFoundError: No module named 'account'`` at startup.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = SRC_DIR / "apps"


def setup_paths() -> None:
    """Make ``src/`` and ``src/apps/`` importable, idempotently."""
    for path in (SRC_DIR, APPS_DIR):
        entry = str(path)
        if entry not in sys.path:
            sys.path.insert(0, entry)
