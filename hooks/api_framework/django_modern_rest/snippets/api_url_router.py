from dmr.routing import Router

from api.v1 import urls as v1_urls

app_name = "api"

#: config.urls builds both the URLconf and the OpenAPI schema from this.
router = Router("api/")
router.include(v1_urls.router, namespace="v1")
