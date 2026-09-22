"""Consistent error envelope for every DRF-handled exception.

Wired up via REST_FRAMEWORK["EXCEPTION_HANDLER"]. That setting is resolved with
django.utils.module_loading.import_string, which splits on the *last* dot -- so
it must point at a module-level callable. A "module.Class.method" path looks
reasonable but fails to import, and DRF then lets every APIException escape as
a 500.
"""

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def flatten_errors(errors, prefix: str = "") -> list[str]:
    """Flatten DRF's nested error structure into ``"field: message"`` strings.

    DRF values can be a str, a list, or a nested dict at any depth, so each
    shape is handled explicitly -- joining a bare str would otherwise iterate
    it character by character.
    """
    if isinstance(errors, dict):
        messages: list[str] = []
        for field, value in errors.items():
            key = f"{prefix}.{field}" if prefix else str(field)
            messages.extend(flatten_errors(value, prefix=key))
        return messages

    if isinstance(errors, (list, tuple)):
        joined = ", ".join(str(item) for item in errors)
        return [f"{prefix}: {joined}" if prefix else joined]

    text = str(errors)
    return [f"{prefix}: {text}" if prefix else text]


def get_error_code(exc: Exception) -> str:
    """Best-effort machine-readable code for the exception."""
    detail = getattr(exc, "detail", None)
    code = getattr(detail, "code", None) or getattr(exc, "default_code", None) or "error"
    return str(code)


def api_exception_handler(exc: Exception, context: dict) -> Response | None:
    """Return DRF's response re-shaped as {success, message, error}.

    Returns None for exceptions DRF does not handle, which lets Django's own
    500 handling (and the Telegram alert) take over.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    messages = flatten_errors(response.data)
    response.data = {
        "success": False,
        "message": "; ".join(messages).strip() or "An unexpected error occurred.",
        "error": get_error_code(exc),
    }
    return response
