from django.test import TestCase


class SchemaTests(TestCase):
    """Controllers are only documented if they are routed through a Router.

    Registering them with plain django.urls.path serves the endpoint but leaves
    it out of the generated schema, which is easy to miss.
    """

    def test_every_endpoint_is_in_the_openapi_schema(self):
        response = self.client.get("/api/schema/")

        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        for expected in (
            "/api/v1/health/",
            "/api/v1/auth/login/",
            "/api/v1/auth/refresh/",
            "/api/v1/auth/verify/",
        ):
            self.assertIn(expected, paths)

    def test_swagger_ui_renders(self):
        self.assertEqual(self.client.get("/api/schema/swagger-ui/").status_code, 200)
