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
        self.assertIn("access_token", body)
        self.assertIn("refresh_token", body)

    def test_bad_password_returns_401(self):
        """Guards DMR_SETTINGS["global_error_handler"].

        A handler that re-raises instead of delegating to dmr's own
        global_error_handler disables its entire 4xx layer, turning every
        authentication failure into a 500.
        """
        self.assertEqual(self.login(password="wrong-password").status_code, 401)

    def test_refresh_returns_a_new_pair(self):
        tokens = self.login().json()

        response = self.client.post(
            "/api/v1/auth/refresh/",
            data={"refresh_token": tokens["refresh_token"]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

    def test_verify_accepts_a_valid_access_token(self):
        tokens = self.login().json()

        response = self.client.post(
            "/api/v1/auth/verify/",
            data={"access_token": tokens["access_token"]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 204)

    def test_verify_rejects_garbage(self):
        response = self.client.post(
            "/api/v1/auth/verify/",
            data={"access_token": "not-a-token"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_refresh_token_is_not_accepted_as_an_access_token(self):
        """dmr checks the `type` claim; a refresh token must not authenticate."""
        tokens = self.login().json()

        response = self.client.post(
            "/api/v1/auth/verify/",
            data={"access_token": tokens["refresh_token"]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
