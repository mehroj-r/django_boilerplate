from core.api.views import BaseController


class HealthAPIView(BaseController):
    """Liveness probe. Public: the container healthcheck calls it."""

    auth = None

    def get(self) -> dict[str, str]:
        return {"status": "ok"}


class TestAPIView(BaseController):
    auth = None

    def get(self) -> dict[str, str]:
        return {"message": "This is a test endpoint."}
