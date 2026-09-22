from dmr.routing import Router

from api.v1.core.urls import auth as auth_urls
from api.v1.core.urls import misc as misc_urls

app_name = "v1"

router = Router("v1/")
router.include(misc_urls.router, namespace="misc")
router.include(auth_urls.router, namespace="auth")
