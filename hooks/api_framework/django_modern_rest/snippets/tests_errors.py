"""The error contract every 4xx/5xx response in this project must satisfy.

The same contract is asserted in the drf flavour of this template, so the two
stay interchangeable for API clients.
"""

from django.test import TestCase, override_settings

from tests.factories import UserFactory

PASSWORD = "Str0ng!Passw0rd"


class ErrorEnvelopeTests(TestCase):
    def assertEnvelope(self, response, *, status_code, error_type):
        self.assertEqual(response.status_code, status_code)
        body = response.json()

        self.assertIs(body["success"], False)
        self.assertIsInstance(body["message"], str)
        self.assertTrue(body["message"])
        self.assertEqual(body["error"]["type"], error_type)

        errors = body["error"]["errors"]
        self.assertTrue(errors)
        for error in errors:
            self.assertEqual({"code", "detail", "attr"}, set(error))
            self.assertIsInstance(error["code"], str)
            self.assertIsInstance(error["detail"], str)
        return body

    def test_validation_error_names_the_field(self):
        """Also guards the msgspec message parsing in core.api.errors.

        msgspec reports the failing field only inside the message text, so
        `attr` is recovered by matching its wording. If msgspec changes that
        wording, `attr` goes null and this test is what notices.
        """
        body = self.assertEnvelope(
            self.client.post("/api/v1/auth/login/", data={}, content_type="application/json"),
            status_code=400,
            error_type="validation_error",
        )

        error = body["error"]["errors"][0]
        self.assertEqual("required", error["code"])
        self.assertIn(error["attr"], {"username", "password"})

    def test_message_is_derived_from_the_errors(self):
        response = self.client.post("/api/v1/auth/login/", data={}, content_type="application/json")

        body = response.json()
        expected = "; ".join(
            f"{error['attr']}: {error['detail']}" if error["attr"] else error["detail"]
            for error in body["error"]["errors"]
        )
        self.assertEqual(expected, body["message"])

    def test_authentication_failure(self):
        """Guards the `responses` override on the JWT controllers.

        dmr's own controllers declare ResponseSpec(ErrorModel, 401), and an
        explicit spec wins over the one derived from error_model -- so without
        the override the enveloped body fails response validation and this
        comes back as a 422.
        """
        user = UserFactory(password=PASSWORD)

        self.assertEnvelope(
            self.client.post(
                "/api/v1/auth/login/",
                data={"username": user.username, "password": "wrong-password"},
                content_type="application/json",
            ),
            status_code=401,
            error_type="client_error",
        )

    def test_method_not_allowed(self):
        body = self.assertEnvelope(
            self.client.post("/api/v1/health/", data={}, content_type="application/json"),
            status_code=405,
            error_type="client_error",
        )

        self.assertEqual("method_not_allowed", body["error"]["errors"][0]["code"])

    def test_not_acceptable(self):
        self.assertEnvelope(
            self.client.get("/api/v1/health/", headers={"accept": "application/xml"}),
            status_code=406,
            error_type="client_error",
        )

    @override_settings(DEBUG=False)
    def test_unrouted_api_path(self):
        """Guards handler404 in config.urls.base; Django only uses it when DEBUG is off."""
        body = self.assertEnvelope(
            self.client.get("/api/v1/does-not-exist/"),
            status_code=404,
            error_type="client_error",
        )

        self.assertEqual("not_found", body["error"]["errors"][0]["code"])


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

    def test_errors_are_documented_as_the_envelope(self):
        schema = self.client.get("/api/schema/").json()

        self.assertIn("ApiError", schema["components"]["schemas"])
        self.assertNotIn("ErrorModel", schema["components"]["schemas"])

    def test_swagger_ui_renders(self):
        self.assertEqual(self.client.get("/api/schema/swagger-ui/").status_code, 200)
