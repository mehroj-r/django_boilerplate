from dmr.routing import Router, path

from api.v1.core.views.auth import LoginAPIView, RefreshAPIView, TokenVerifyAPIView

app_name = "auth"

# Router, not django.urls.path: it carries the OpenAPI metadata.
router = Router(
    "auth/",
    [
        path("login/", LoginAPIView.as_view(), name="login"),
        path("refresh/", RefreshAPIView.as_view(), name="token_refresh"),
        path("verify/", TokenVerifyAPIView.as_view(), name="token_verify"),
    ],
    tags=["auth"],
)
