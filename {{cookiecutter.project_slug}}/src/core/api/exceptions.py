"""Where this project maps its own exception types onto DRF ones.

The response *shape* lives in core.api.errors; this module only decides which
DRF exception a non-DRF error should be reported as. Anything not converted
here escapes as a 500 (and reaches Sentry), which is usually what you want.
"""

from drf_standardized_errors.handler import ExceptionHandler


class ApiExceptionHandler(ExceptionHandler):
    """Wired up via DRF_STANDARDIZED_ERRORS["EXCEPTION_HANDLER_CLASS"]."""

    def convert_known_exceptions(self, exc: Exception) -> Exception:
        # if isinstance(exc, MyDomainError):
        #     return rest_framework.exceptions.ValidationError(str(exc))
        return super().convert_known_exceptions(exc)
