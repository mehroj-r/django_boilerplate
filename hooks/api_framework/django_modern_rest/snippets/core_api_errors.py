"""The project-wide error envelope, and the schema that matches it.

dmr's own error payload is ``{"detail": [{"msg", "type", "loc"}]}``. This module
reshapes it into the ``{success, message, error}`` envelope the rest of the API
uses, so a client can read ``success`` on every response regardless of status.

The drf flavour of this template ships a different implementation of this same
module producing byte-identical bodies.
"""

import re
from http import HTTPStatus
from typing import Any, Literal

from django.conf import settings
from django.utils.encoding import force_str
from dmr.errors import ErrorDetail, ErrorType
from dmr.exceptions import (
    DataRenderingError,
    InternalServerError,
    NotAcceptableError,
    NotAuthenticatedError,
    RequestSerializationError,
    ResponseSchemaError,
    TooManyRequestsError,
    ValidationError,
)
from typing_extensions import TypedDict

FALLBACK_MESSAGE = "An unexpected error occurred."

EnvelopeType = Literal["validation_error", "client_error", "server_error"]


class ApiErrorItem(TypedDict):
    """One error, shaped like a drf-standardized-errors item."""

    code: str
    detail: str
    attr: str | None


class ApiErrorDetail(TypedDict):
    type: EnvelopeType
    errors: list[ApiErrorItem]


class ApiError(TypedDict):
    """Every error body in this project. Used as ``Controller.error_model``."""

    # Not Literal[False]: msgspec only allows None/int/str in a Literal.
    success: bool
    message: str
    error: ApiErrorDetail


#: dmr nests each request part under the endpoint parameter that receives it.
_CONTEXT_NAMES = frozenset(
    {
        "parsed_body",
        "parsed_cookies",
        "parsed_file_metadata",
        "parsed_headers",
        "parsed_path",
        "parsed_query",
    }
)

#: msgspec appends the failing path: "Expected `str`, got `int` - at `$.a.b`".
_MSGSPEC_LOCATION = re.compile(r"\A(?P<detail>.*?) - at `\$(?P<path>[^`]*)`\Z", re.DOTALL)
_MSGSPEC_MISSING = re.compile(r"\AObject missing required field `(?P<field>[^`]+)`\Z")

_CODE_BY_EXCEPTION = {
    DataRenderingError: "error",
    InternalServerError: "error",
    NotAcceptableError: "not_acceptable",
    NotAuthenticatedError: "not_authenticated",
    RequestSerializationError: "parse_error",
    ResponseSchemaError: "error",
    TooManyRequestsError: "throttled",
}

_CODE_BY_ERROR_TYPE = {
    ErrorType.internal_error: "error",
    ErrorType.not_allowed: "method_not_allowed",
    ErrorType.not_found: "not_found",
    ErrorType.ratelimit: "throttled",
    ErrorType.security: "permission_denied",
    ErrorType.streaming: "error",
    ErrorType.user_msg: "error",
    ErrorType.value_error: "invalid",
}

#: Only consulted when no status code is available, which is the case for the
#: plain-string errors dmr raises for 404, 405 and 500.
_TYPE_BY_ERROR_TYPE = {
    ErrorType.internal_error: "server_error",
    ErrorType.streaming: "server_error",
    ErrorType.value_error: "validation_error",
}


def format_error(
    error: str | Exception,
    *,
    loc: str | list[str | int] | None = None,
    error_type: str | ErrorType | None = None,
    status_code: HTTPStatus | int | None = None,
) -> ApiError:
    """Drop-in replacement for ``dmr.errors.format_error``.

    *status_code* is our own addition. dmr never passes it, but it is the only
    way a plain-string error can be told apart from a client one, so
    ``BaseController.fail()`` and your own handlers should.
    """
    if isinstance(error, ValidationError):
        return build_envelope(
            [_item_from_detail(detail) for detail in error.payload],
            status_code or error.status_code,
        )

    code = None
    if type(error) in _CODE_BY_EXCEPTION:
        code = _CODE_BY_EXCEPTION[type(error)]
        status_code = status_code or error.status_code
        if isinstance(error, (InternalServerError, DataRenderingError)):
            # Same rule as dmr: the real cause only leaks while debugging.
            error = str(error) if settings.DEBUG else force_str(InternalServerError.default_message)
        else:
            error = force_str(error.args[0])

    if isinstance(error, str):
        resolved = _resolve_error_type(error_type)
        return build_envelope(
            [
                {
                    "code": code or _CODE_BY_ERROR_TYPE.get(resolved, "error"),
                    "detail": error,
                    "attr": _attr_from_loc(loc),
                },
            ],
            status_code,
            fallback_type=_TYPE_BY_ERROR_TYPE.get(resolved, "client_error"),
        )

    raise NotImplementedError(f"Cannot format error {error!r} of type {type(error)} safely")


def build_envelope(
    errors: list[ApiErrorItem],
    status_code: HTTPStatus | int | None,
    *,
    fallback_type: EnvelopeType = "client_error",
) -> ApiError:
    return {
        "success": False,
        "message": build_message(errors),
        "error": {
            "type": _envelope_type(status_code, fallback_type),
            "errors": errors,
        },
    }


def build_message(errors: list[ApiErrorItem]) -> str:
    """Collapse the individual errors into the envelope's one-line summary."""
    parts = [f"{error['attr']}: {error['detail']}" if error.get("attr") else error["detail"] for error in errors]
    return "; ".join(parts).strip() or FALLBACK_MESSAGE


def _resolve_error_type(error_type: Any) -> ErrorType | None:
    try:
        return ErrorType(error_type)
    except ValueError:
        return None


def _envelope_type(status_code: HTTPStatus | int | None, fallback: EnvelopeType) -> EnvelopeType:
    if status_code is None:
        return fallback
    if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return "server_error"
    if status_code in {HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY}:
        return "validation_error"
    return "client_error"


def _item_from_detail(detail: ErrorDetail) -> ApiErrorItem:
    """Convert one dmr ``ErrorDetail`` into an envelope item.

    The pydantic plugin fills ``loc``; msgspec does not, and puts the failing
    path in the message instead, so it is recovered from there. Best-effort by
    design: an unrecognised message yields ``attr: null`` rather than raising.
    """
    text = force_str(detail["msg"])
    code = _CODE_BY_ERROR_TYPE.get(_resolve_error_type(detail.get("type")), "invalid")
    path: list[str | int] = list(detail.get("loc") or [])

    location = _MSGSPEC_LOCATION.match(text)
    if location is not None:
        text = location.group("detail")
        if not path:
            path = [part for part in location.group("path").split(".") if part]

    missing = _MSGSPEC_MISSING.match(text)
    if missing is not None:
        path.append(missing.group("field"))
        code = "required"
        text = "This field is required."

    return {"code": code, "detail": text, "attr": _attr_from_loc(path)}


def _attr_from_loc(loc: str | list[str | int] | None) -> str | None:
    if loc is None:
        return None
    parts = [str(part) for part in ([loc] if isinstance(loc, str) else loc) if str(part)]
    if parts and parts[0] in _CONTEXT_NAMES:
        parts = parts[1:]
    return ".".join(parts) or None
