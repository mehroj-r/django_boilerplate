from django.test import TestCase

from account.models import User
from tests.factories import UserFactory


class UserModelTests(TestCase):
    def test_create_user_hashes_the_password(self):
        user = User.objects.create_user(username="alice", password="Str0ng!Passw0rd", email="a@example.com")

        self.assertNotEqual(user.password, "Str0ng!Passw0rd")
        self.assertTrue(user.check_password("Str0ng!Passw0rd"))

    def test_unusable_password_stays_unusable(self):
        """Regression guard.

        An earlier User.save() re-hashed anything not starting with
        "pbkdf2_sha256$", which mangled set_unusable_password()'s "!" marker
        into a valid hash of that marker.
        """
        user = UserFactory()
        user.set_unusable_password()
        user.save()

        user.refresh_from_db()
        self.assertFalse(user.has_usable_password())

    def test_password_is_not_rehashed_on_every_save(self):
        user = UserFactory(password="Str0ng!Passw0rd")
        hashed = user.password

        user.first_name = "Renamed"
        user.save()
        user.refresh_from_db()

        self.assertEqual(user.password, hashed)
        self.assertTrue(user.check_password("Str0ng!Passw0rd"))

    def test_create_superuser_requires_staff_and_superuser(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(username="bob", password="x", email="b@example.com", is_staff=False)

    def test_navigation_title_omits_a_missing_last_name(self):
        user = UserFactory(first_name="Ada", last_name=None)
        self.assertEqual(user.get_navigation_title(), "Ada")


class SoftDeleteTests(TestCase):
    def test_delete_is_soft_and_managers_partition_correctly(self):
        user = UserFactory()

        user.delete()

        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertTrue(User.deleted_objects.filter(pk=user.pk).exists())
        self.assertTrue(User.global_objects.filter(pk=user.pk).exists())

    def test_restore_brings_the_row_back(self):
        user = UserFactory()
        user.delete()

        User.deleted_objects.get(pk=user.pk).restore()

        self.assertTrue(User.objects.filter(pk=user.pk).exists())
