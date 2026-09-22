from rest_framework import generics, mixins, status
from rest_framework.response import Response

from core.api.errors import envelope_from_data


class CustomResponseMixin:
    """
    Mixin to customize API responses with a standard structure.
    It provides methods to format successful and error responses.
    The response structure is as follows:
    - For success:
        {
            "success": true,
            "message": <SUCCESS_MESSAGE>,
            "data": <response_data>
        }
    - For error:
        {
            "success": false,
            "message": <summary>,
            "error": {"type": <type>, "errors": [{"code", "detail", "attr"}]}
        }
    Raised exceptions are enveloped by drf-standardized-errors instead (see
    core.api.errors); this mixin only catches 4xx responses a view returned by
    hand, which carry no per-field detail to report.
    """

    SUCCESS_MESSAGE = "OK"
    NO_BODY_STATUS_CODES = {
        status.HTTP_204_NO_CONTENT,
        status.HTTP_205_RESET_CONTENT,
        status.HTTP_304_NOT_MODIFIED,
    }

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if not isinstance(response, Response):
            return response

        if response.status_code in self.NO_BODY_STATUS_CODES:
            return response

        # Paginated list responses already carry the envelope (see
        # core.utils.pagination.CustomPagination), so leave them alone.
        if self._is_structured_response(response):
            return response

        if response.status_code < 400:
            return self._success_response(response=response)
        return self._error_response(response=response)

    def _success_response(self, response: Response) -> Response:
        response.data = {
            "success": True,
            "message": self.SUCCESS_MESSAGE,
            "data": response.data,
        }
        return response

    def _error_response(self, response: Response) -> Response:
        response.data = envelope_from_data(response.data, response.status_code)
        return response

    @staticmethod
    def _is_structured_response(response: Response) -> bool:
        return isinstance(response.data, dict) and "success" in response.data and "message" in response.data


class BaseAPIView(CustomResponseMixin, generics.GenericAPIView):
    """Base for every endpoint in this project.

    Permissions come from REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]
    (IsAuthenticated); override `permission_classes` per view to widen access.
    """


class ListAPIView(mixins.ListModelMixin, BaseAPIView):
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CreateAPIView(mixins.CreateModelMixin, BaseAPIView):
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class RetrieveAPIView(mixins.RetrieveModelMixin, BaseAPIView):
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class UpdateAPIView(mixins.UpdateModelMixin, BaseAPIView):
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class DestroyAPIView(mixins.DestroyModelMixin, BaseAPIView):
    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
