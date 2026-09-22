"""Project-level manager extension points.

These subclass django-soft-delete's managers unchanged so that project-wide
queryset behaviour can be added in one place later without touching every
model. Keep them thin -- model-specific queries belong on the model's own
manager.
"""

from django_softdelete.managers import DeletedManager as DjangoDeletedManager
from django_softdelete.managers import GlobalManager as DjangoGlobalManager
from django_softdelete.managers import SoftDeleteManager as DjangoSoftDeleteManager


class SoftDeleteManager(DjangoSoftDeleteManager):
    """Default manager: only rows that have not been soft-deleted."""


class DeletedManager(DjangoDeletedManager):
    """Only rows that have been soft-deleted."""


class GlobalManager(DjangoGlobalManager):
    """Every row, deleted or not."""
