from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView, RedocView, SwaggerView

from api.url_router import router as api_router

schema = build_schema(api_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    api_router.to_urlpatterns(namespace="api"),
    path("api/schema/", OpenAPIJsonView.as_view(schema=schema), name="schema"),
    path("api/schema/swagger-ui/", SwaggerView.as_view(schema=schema), name="swagger-ui"),
    path("api/schema/redoc/", RedocView.as_view(schema=schema), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    from config.urls import dev

    urlpatterns += dev.urlpatterns
