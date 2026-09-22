from dmr.routing import Router

from api.v1 import urls as v1_urls

app_name = "api"

#: Root of the API router tree. config.urls builds both the URLconf and the
#: OpenAPI schema from this single object, so every route reachable under /api/
#: is documented by construction.
router = Router("api/")
router.include(v1_urls.router, namespace="v1")
