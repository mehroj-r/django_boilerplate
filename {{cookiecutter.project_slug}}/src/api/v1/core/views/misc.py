from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response

from core.api.views import BaseAPIView


@extend_schema(
    summary="Liveness probe",
    responses=inline_serializer("HealthResponse", {"status": serializers.CharField()}),
    examples=[OpenApiExample("ok", value={"success": True, "message": "OK", "data": {"status": "ok"}})],
)
class HealthAPIView(BaseAPIView):
    """Liveness probe. Public: the container healthcheck calls it."""

    permission_classes = ()
    authentication_classes = ()

    def get(self, request, *args, **kwargs):
        return Response(data={"status": "ok"}, status=200)


@extend_schema(
    summary="Example endpoint",
    responses=inline_serializer("TestResponse", {"message": serializers.CharField()}),
)
class TestAPIView(BaseAPIView):
    permission_classes = ()
    authentication_classes = ()

    def get(self, request, *args, **kwargs):
        return Response(data={"message": "This is a test endpoint."}, status=200)
