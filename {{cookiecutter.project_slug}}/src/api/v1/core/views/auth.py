from rest_framework_simplejwt.serializers import TokenVerifySerializer
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from core.api.views import BaseAPIView


class LoginAPIView(TokenObtainPairView, BaseAPIView):
    pass


class RefreshAPIView(TokenRefreshView, BaseAPIView):
    pass


class TokenVerifyAPIView(TokenVerifyView, BaseAPIView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            serializer = TokenVerifySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            response.data = {"detail": "Token is valid"}

        return response
