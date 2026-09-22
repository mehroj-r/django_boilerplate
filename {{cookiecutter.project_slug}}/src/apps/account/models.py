from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from account import managers
from core.models import SoftDeleteModel, TimestampedModel


class User(AbstractBaseUser, TimestampedModel, SoftDeleteModel):
    first_name = models.CharField(max_length=30, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=30, blank=True, null=True, verbose_name=_("Last Name"))
    patronymic = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Patronymic"))

    username = models.CharField(max_length=150, unique=True, verbose_name=_("Username"))
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name=_("Phone Number"))
    email = models.EmailField(unique=True, verbose_name=_("Email"))

    # For Django Admin
    is_staff = models.BooleanField(default=False, verbose_name=_("Is staff"))
    is_superuser = models.BooleanField(default=False, verbose_name=_("Is superuser"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["first_name", "email"]

    objects = managers.UserManager()

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return f"{self.first_name} (@{self.get_username()})"

    def get_navigation_title(self):
        return " ".join(part for part in (self.first_name, self.last_name) if part)

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    def restore(self, *args, strict: bool = False, **kwargs):
        """Restore a soft-deleted user.

        django-soft-delete defaults to strict=True, which refuses to restore a
        row that is referenced by any non-soft-delete model. The user model is
        always referenced by django.contrib.admin's LogEntry (and by sessions),
        so strict restore can never succeed here. Domain models keep the strict
        default.
        """
        return super().restore(*args, strict=strict, **kwargs)
