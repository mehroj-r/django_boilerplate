from django.test import TestCase
from django.urls import reverse


class HealthEndpointTests(TestCase):
    """The container HEALTHCHECK and the CI smoke test both call this URL.

    If the path moves, the Docker healthcheck silently probes a 404 -- keep
    this test and scripts/healthcheck.sh in agreement.
    """

    def test_health_is_public_and_wrapped(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"success": True, "message": "OK", "data": {"status": "ok"}},
        )

    def test_health_reverses_to_the_documented_path(self):
        self.assertEqual(reverse("api:v1:misc:health"), "/api/v1/health/")
