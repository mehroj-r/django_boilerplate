"""The error contract every 4xx/5xx response in this project must satisfy.

The same contract is asserted in the django-modern-rest flavour of this
template, so the two stay interchangeable for API clients.
"""

from django.test import TestCase

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
        body = self.assertEnvelope(
            self.client.post("/api/v1/auth/login/", data={}, content_type="application/json"),
            status_code=400,
            error_type="validation_error",
        )

        attrs = {error["attr"] for error in body["error"]["errors"]}
        self.assertIn("password", attrs)
        self.assertEqual("required", body["error"]["errors"][0]["code"])

    def test_message_is_derived_from_the_errors(self):
        response = self.client.post("/api/v1/auth/login/", data={}, content_type="application/json")

        body = response.json()
        expected = "; ".join(f"{error['attr']}: {error['detail']}" for error in body["error"]["errors"])
        self.assertEqual(expected, body["message"])

    def test_authentication_failure(self):
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

    def test_unsupported_media_type(self):
        self.assertEnvelope(
            self.client.post("/api/v1/auth/login/", data="username=x", content_type="text/plain"),
            status_code=415,
            error_type="client_error",
        )

    def test_method_not_allowed(self):
        body = self.assertEnvelope(
            self.client.post("/api/v1/health/", data={}, content_type="application/json"),
            status_code=405,
            error_type="client_error",
        )

        self.assertEqual("method_not_allowed", body["error"]["errors"][0]["code"])
