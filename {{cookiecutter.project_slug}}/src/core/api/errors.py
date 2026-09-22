"""The project-wide error envelope, and the OpenAPI schema that matches it.

drf-standardized-errors produces ``{"type": ..., "errors": [...]}``. This module
places that payload inside the ``{success, message, ...}`` envelope the rest of
the API uses (see core.api.views.CustomResponseMixin), so a client can read
``success`` on every response regardless of status code.

The DMR flavour of this template ships a different implementation of this same
module producing byte-identical bodies.
"""

from dataclasses import asdict

from drf_spectacular.utils import PolymorphicProxySerializer
from drf_standardized_errors.formatter import ExceptionFormatter
from drf_standardized_errors.openapi import AutoSchema
from drf_standardized_errors.types import ErrorResponse
from rest_framework import serializers

FALLBACK_MESSAGE = "An unexpected error occurred."


def build_message(errors: list[dict]) -> str:
    """Collapse the individual errors into the envelope's one-line summary."""
    parts = [f"{error['attr']}: {error['detail']}" if error.get("attr") else error["detail"] for error in errors]
    return "; ".join(parts).strip() or FALLBACK_MESSAGE


def build_envelope(error_type: str, errors: list[dict]) -> dict:
    return {
        "success": False,
        "message": build_message(errors),
        "error": {"type": error_type, "errors": errors},
    }


def envelope_from_data(data, status_code: int) -> dict:
    """Envelope a 4xx/5xx body that was returned rather than raised.

    drf-standardized-errors only sees exceptions, so a view returning
    ``Response(status=400, ...)`` by hand would otherwise escape the contract.
    Raising is still preferred: it keeps the per-field detail this cannot
    reconstruct.
    """
    error_type = "server_error" if status_code >= 500 else "client_error"
    detail = data if isinstance(data, str) else str(data)
    return build_envelope(error_type, [{"code": "error", "detail": detail, "attr": None}])


class EnvelopedExceptionFormatter(ExceptionFormatter):
    """Wired up via DRF_STANDARDIZED_ERRORS["EXCEPTION_FORMATTER_CLASS"]."""

    def format_error_response(self, error_response: ErrorResponse) -> dict:
        errors = [asdict(error) for error in error_response.errors]
        return build_envelope(error_response.type, errors)


#: Wrappers are reused across operations and across schema rebuilds. Keying on
#: the component name rather than the class matters: drf-standardized-errors
#: builds a fresh validation-error class per operation on every schema request,
#: so keying on the class would leak and would let two classes claim one name.
_ENVELOPE_SERIALIZERS: dict[str, type[serializers.Serializer]] = {}


def _ref_name(inner) -> str | None:
    return getattr(getattr(inner, "Meta", None), "ref_name", None)


def _envelope_serializer(inner):
    """Build the serializer describing an enveloped `inner` error payload."""
    # ERROR_SCHEMAS entries may be instances rather than classes.
    inner_class = inner if isinstance(inner, type) else type(inner)
    base_name = _ref_name(inner_class) or inner_class.__name__
    name = f"Enveloped{base_name}"

    if name not in _ENVELOPE_SERIALIZERS:
        attributes = {
            "success": serializers.BooleanField(),
            "message": serializers.CharField(),
            "error": inner if not isinstance(inner, type) else inner(),
        }
        if _ref_name(inner_class):
            attributes["Meta"] = type("Meta", (), {"ref_name": name})
        _ENVELOPE_SERIALIZERS[name] = type(name, (serializers.Serializer,), attributes)

    return _ENVELOPE_SERIALIZERS[name]


class EnvelopedAutoSchema(AutoSchema):
    """Documents the enveloped bodies that EnvelopedExceptionFormatter returns.

    Without this the schema would advertise drf-standardized-errors' unwrapped
    payload and silently disagree with every real error response.
    """

    def _get_error_response_serializer(self, status_code: str):
        inner = super()._get_error_response_serializer(status_code)
        if inner is None:
            return None

        if isinstance(inner, PolymorphicProxySerializer):
            members = inner.serializers
            # 400 is a oneOf over per-field validation serializers. Wrapping the
            # members rather than the proxy keeps each variant documented; the
            # `type` discriminator moves to `error.type`, which OpenAPI cannot
            # express, so it is dropped.
            return PolymorphicProxySerializer(
                component_name=f"Enveloped{inner.component_name}",
                serializers=[
                    _envelope_serializer(member)
                    for member in (members.values() if isinstance(members, dict) else members)
                ],
                resource_type_field_name=None,
            )

        return _envelope_serializer(inner)
