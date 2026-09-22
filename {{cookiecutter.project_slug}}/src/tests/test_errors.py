from django.test import SimpleTestCase
from rest_framework.exceptions import NotFound, ValidationError

from core.api.exceptions import flatten_errors, get_error_code


class FlattenErrorsTests(SimpleTestCase):
    def test_list_values_are_joined(self):
        self.assertEqual(
            flatten_errors({"email": ["Invalid.", "Too long."]}),
            ["email: Invalid., Too long."],
        )

    def test_plain_string_value_is_not_iterated_per_character(self):
        """A bare str used to be fed to ", ".join(), yielding "f, i, e, l, d"."""
        self.assertEqual(flatten_errors({"detail": "Not found."}), ["detail: Not found."])

    def test_nested_dicts_are_dotted(self):
        self.assertEqual(
            flatten_errors({"profile": {"phone": ["Required."]}}),
            ["profile.phone: Required."],
        )

    def test_top_level_list(self):
        self.assertEqual(flatten_errors(["Bad.", "Worse."]), ["Bad., Worse."])


class ErrorCodeTests(SimpleTestCase):
    def test_uses_the_drf_error_code(self):
        self.assertEqual(get_error_code(NotFound()), "not_found")

    def test_falls_back_for_unknown_exceptions(self):
        self.assertEqual(get_error_code(ValueError("boom")), "error")

    def test_validation_error(self):
        self.assertEqual(get_error_code(ValidationError("nope")), "invalid")
