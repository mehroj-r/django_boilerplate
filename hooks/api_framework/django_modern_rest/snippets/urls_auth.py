from dmr.routing import Router, path

from api.v1.core.views.auth import LoginAPIView, RefreshAPIView, TokenVerifyAPIView

app_name = "auth"

# dmr controllers must be registered through a Router: it is what carries the
# OpenAPI metadata that dmr.openapi.build_schema() reads. Plain django.urls.path
# would serve the endpoint but leave it out of the schema.
router = Router(
    "auth/",
    [
        path("login/", LoginAPIView.as_view(), name="login"),
        path("refresh/", RefreshAPIView.as_view(), name="token_refresh"),
        path("verify/", TokenVerifyAPIView.as_view(), name="token_verify"),
    ],
    tags=["auth"],
)
