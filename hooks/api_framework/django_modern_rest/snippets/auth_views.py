import datetime as dt
from http import HTTPStatus
from typing import TypedDict

from dmr import HeaderSpec, ResponseSpec
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security.jwt.views import (
    ObtainTokensPayload,
    ObtainTokensResponse,
    ObtainTokensSyncController,
    RefreshTokenSyncController,
    VerifyTokenSyncController,
)

from core.api.errors import ApiError
from core.api.views import ErrorEnvelopeMixin

#: dmr's JWT controllers hardcode ResponseSpec(ErrorModel, 401), and an
#: explicit spec beats the one auth derives from error_model. Without this
#: override the enveloped body fails response validation and the caller gets a
#: 422 instead of a 401.
UNAUTHORIZED = (
    ResponseSpec(
        ApiError,
        status_code=HTTPStatus.UNAUTHORIZED,
        description="Raised when auth was not successful",
        headers={
            # These endpoints issue credentials rather than requiring them, so
            # there is no auth chain to build a challenge from and the header
            # is absent in practice. Declared anyway: an undescribed header on
            # a validated response is rejected, so this keeps adding auth later
            # from turning every 401 into a 422.
            "WWW-Authenticate": HeaderSpec(
                description="Challenges that the client can use to authenticate this request",
                required=False,
                skip_validation=True,
            ),
        },
    ),
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
    ErrorEnvelopeMixin,
    TokenResponseMixin,
    ObtainTokensSyncController[MsgspecSerializer, LoginPayload, ObtainTokensResponse],
):
    auth = None
    responses = UNAUTHORIZED

    def convert_auth_payload(self, payload: LoginPayload) -> ObtainTokensPayload:
        return {
            "username": payload["username"],
            "password": payload["password"],
        }


class RefreshAPIView(
    ErrorEnvelopeMixin,
    TokenResponseMixin,
    RefreshTokenSyncController[MsgspecSerializer, RefreshPayload, ObtainTokensResponse],
):
    auth = None
    responses = UNAUTHORIZED

    def convert_refresh_payload(self, payload: RefreshPayload) -> str:
        return payload["refresh_token"]


class TokenVerifyAPIView(ErrorEnvelopeMixin, VerifyTokenSyncController[MsgspecSerializer, VerifyPayload]):
    """Returns 204 when the access token is valid, 401 otherwise."""

    auth = None
    responses = UNAUTHORIZED

    def convert_verify_payload(self, payload: VerifyPayload) -> str:
        return payload["access_token"]
