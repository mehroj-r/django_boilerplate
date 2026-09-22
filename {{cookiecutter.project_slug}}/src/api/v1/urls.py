from django.urls import include, path

app_name = "v1"

urlpatterns = [
    path("", include("api.v1.core.urls.misc", namespace="misc")),
    path("users/", include("api.v1.account.urls", namespace="account")),
    path("auth/", include("api.v1.core.urls.auth", namespace="auth")),
]
