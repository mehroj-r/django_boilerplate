from django.test import TestCase

from tests.factories import UserFactory

PASSWORD = "Str0ng!Passw0rd"


class JWTAuthTests(TestCase):
    def setUp(self):
        self.user = UserFactory(password=PASSWORD)

    def login(self, password=PASSWORD):
        return self.client.post(
            "/api/v1/auth/login/",
            data={"username": self.user.username, "password": password},
            content_type="application/json",
        )

    def test_login_returns_token_pair(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertIn("access", body["data"])
        self.assertIn("refresh", body["data"])

    def test_bad_password_returns_401_in_the_error_envelope(self):
        """Guards REST_FRAMEWORK["EXCEPTION_HANDLER"].

        See tests.test_errors for the full error contract; this only checks
        that the auth endpoints go through it too.
        """
        response = self.login(password="wrong-password")

        self.assertEqual(response.status_code, 401)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertIn("error", body)

    def test_missing_field_returns_400_naming_the_field(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            data={"username": self.user.username},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["message"])

    def test_refresh_and_verify(self):
        tokens = self.login().json()["data"]

        refresh = self.client.post(
            "/api/v1/auth/refresh/",
            data={"refresh": tokens["refresh"]},
            content_type="application/json",
        )
        self.assertEqual(refresh.status_code, 200)

        verify = self.client.post(
            "/api/v1/auth/verify/",
            data={"token": tokens["access"]},
            content_type="application/json",
        )
        self.assertEqual(verify.status_code, 200)

    def test_protected_endpoint_requires_a_token(self):
        self.assertEqual(self.client.get("/api/v1/test/").status_code, 200)  # public
