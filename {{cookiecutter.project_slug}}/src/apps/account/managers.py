from django.contrib.auth.base_user import BaseUserManager
from django_softdelete.managers import SoftDeleteManager


class UserManager(SoftDeleteManager, BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        """Returns the user by their username field."""
        return self.get(**{self.model.USERNAME_FIELD: username})

    def create_user(self, username, password=None, **extra_fields):
        """Create a user, hashing the password on the way in."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        """Create a superuser. is_staff/is_superuser must both be True."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(username, password, **extra_fields)

    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError(f"The {self.model.USERNAME_FIELD} field must be set.")

        email = extra_fields.get("email")
        if email:
            extra_fields["email"] = self.normalize_email(email)

        user = self.model(**{self.model.USERNAME_FIELD: username}, **extra_fields)
        # set_password is the single place a raw password is hashed. Never hash
        # in Model.save(): it cannot tell a raw password from an already-hashed
        # one, and it mangles set_unusable_password()'s "!" marker.
        user.set_password(password)
        user.save(using=self._db)
        return user
