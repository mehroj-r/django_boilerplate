from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from account.models import User
from core.admin import BaseSoftDeleteModelAdmin


class UserAdminCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone")


class UserAdminChangeForm(UserChangeForm):
    """Renders the stored hash read-only instead of as an editable text field."""

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseSoftDeleteModelAdmin, DjangoUserAdmin):
    """User admin.

    Inherits Django's UserAdmin for correct password handling (hashed on
    create, read-only hash + separate change form on edit) and
    BaseSoftDeleteModelAdmin for the soft-delete queryset and actions.
    """

    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    # This model uses AbstractBaseUser without PermissionsMixin, so there are
    # no groups/user_permissions m2m fields to lay out horizontally.
    filter_horizontal = ()

    list_display = ("id", "username", "phone", "first_name", "last_name", "is_active", "is_staff", "is_deleted")
    list_display_links = ("id", "username")
    search_fields = ("username", "phone", "email", "first_name", "last_name", "patronymic")
    list_filter = ("is_active", "is_staff", "is_superuser")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "last_login", "deleted_at", "restored_at", "transaction_id")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "patronymic", "email", "phone")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser")}),
        (_("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
        (_("Soft delete"), {"fields": ("deleted_at", "restored_at", "transaction_id"), "classes": ("collapse",)}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
