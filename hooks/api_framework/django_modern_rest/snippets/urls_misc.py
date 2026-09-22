from dmr.routing import Router, path

from api.v1.core.views.misc import HealthAPIView, TestAPIView

app_name = "misc"

# Mounted at the version root so the liveness probe is /api/v1/health/.
router = Router(
    "",
    [
        path("health/", HealthAPIView.as_view(), name="health"),
        path("test/", TestAPIView.as_view(), name="test"),
    ],
    tags=["misc"],
)
