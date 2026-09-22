from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView, RedocView, SwaggerView
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import build_404_handler, build_500_handler

from api.url_router import router as api_router
from core.api.errors import format_error as format_error_envelope

schema = build_schema(api_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    api_router.to_urlpatterns(namespace="api"),
    path("api/schema/", OpenAPIJsonView.as_view(schema=schema), name="schema"),
    path("api/schema/swagger-ui/", SwaggerView.as_view(schema=schema), name="swagger-ui"),
    path("api/schema/redoc/", RedocView.as_view(schema=schema), name="redoc"),
]

#: Django resolves these by name from ROOT_URLCONF. They only fire when DEBUG
#: is off, and only under the prefixes listed here -- everything else keeps
#: Django's HTML pages.
handler404 = build_404_handler("api/", serializer=MsgspecSerializer, format_error=format_error_envelope)
handler500 = build_500_handler("api/", serializer=MsgspecSerializer, format_error=format_error_envelope)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    from config.urls import dev

    urlpatterns += dev.urlpatterns
