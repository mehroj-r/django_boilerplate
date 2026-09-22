from django.db import models
from django.utils.translation import gettext_lazy as _
from django_softdelete.models import SoftDeleteModel as DjangoSoftDeleteModel

from core.managers import DeletedManager, GlobalManager, SoftDeleteManager


class BaseModel(models.Model):
    objects = models.Manager()

    class Meta:
        abstract = True


class TimestampedModel(BaseModel):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        abstract = True


class SoftDeleteModel(DjangoSoftDeleteModel, BaseModel):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name=_("Deleted At"))
    restored_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Restored At"))
    transaction_id = models.UUIDField(null=True, blank=True, verbose_name=_("Transaction ID"))

    objects = SoftDeleteManager()
    deleted_objects = DeletedManager()
    global_objects = GlobalManager()

    class Meta:
        abstract = True
