import datetime as dt
from typing import TypedDict

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security.jwt.views import (
    ObtainTokensPayload,
    ObtainTokensResponse,
    ObtainTokensSyncController,
    RefreshTokenSyncController,
    VerifyTokenSyncController,
)


class LoginPayload(TypedDict):
    """Request body for POST /api/v1/auth/login/."""

    username: str
    password: str


class RefreshPayload(TypedDict):
    """Request body for POST /api/v1/auth/refresh/."""

    refresh_token: str


class VerifyPayload(TypedDict):
    """Request body for POST /api/v1/auth/verify/."""

    access_token: str


class TokenResponseMixin:
    """Builds the access/refresh pair returned by login and refresh."""

    def make_api_response(self) -> ObtainTokensResponse:
        now = dt.datetime.now(dt.UTC)
        return {
            "access_token": self.create_jwt_token(
                token_type="access",  # noqa: S106  (JWT claim, not a password)
                expiration=now + self.jwt_expiration,
            ),
            "refresh_token": self.create_jwt_token(
                token_type="refresh",  # noqa: S106  (JWT claim, not a password)
                expiration=now + self.jwt_refresh_expiration,
            ),
        }


class LoginAPIView(
    TokenResponseMixin,
    ObtainTokensSyncController[MsgspecSerializer, LoginPayload, ObtainTokensResponse],
):
    auth = ()

    def convert_auth_payload(self, payload: LoginPayload) -> ObtainTokensPayload:
        return {
            "username": payload["username"],
            "password": payload["password"],
        }


class RefreshAPIView(
    TokenResponseMixin,
    RefreshTokenSyncController[MsgspecSerializer, RefreshPayload, ObtainTokensResponse],
):
    auth = ()

    def convert_refresh_payload(self, payload: RefreshPayload) -> str:
        return payload["refresh_token"]


class TokenVerifyAPIView(VerifyTokenSyncController[MsgspecSerializer, VerifyPayload]):
    """Returns 204 when the access token is valid, 401 otherwise."""

    auth = ()

    def convert_verify_payload(self, payload: VerifyPayload) -> str:
        return payload["access_token"]
