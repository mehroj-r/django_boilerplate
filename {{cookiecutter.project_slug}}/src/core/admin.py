from typing import Any

from django.contrib.admin import ModelAdmin
from django_softdelete.admin import (
    HARD_DELETE_ACTION,
    REGULAR_DELETE_ACTION_NAME,
    RESTORE_ACTION,
    SOFT_DELETE_ACTION,
)
from django_softdelete.filters import SoftDeleteFilter


class BaseModelAdmin(ModelAdmin):
    pass


class BaseSoftDeleteModelAdmin(BaseModelAdmin):
    """Admin for SoftDeleteModel subclasses.

    Shows deleted rows alongside live ones and swaps Django's delete action for
    soft-delete / restore / hard-delete, chosen by the current filter.
    """

    def get_queryset(self, request) -> Any:
        # Mirrors ModelAdmin.get_queryset but reads through global_objects so
        # soft-deleted rows stay visible in the changelist.
        queryset = self.model.global_objects.get_queryset()
        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset

    def get_list_filter(self, request) -> Any:
        list_filter = list(super().get_list_filter(request) or [])
        if SoftDeleteFilter not in list_filter:
            list_filter.append(SoftDeleteFilter)
        return list_filter

    def get_actions(self, request) -> Any:
        actions = super().get_actions(request)
        actions.pop(REGULAR_DELETE_ACTION_NAME, None)

        # SoftDeleteFilter only ever sets "true" or "false"; anything else (an
        # absent filter, or a hand-typed query string) means "show everything".
        # A dict lookup here would raise KeyError and 500 the changelist.
        deleted_filter_value = request.GET.get(SoftDeleteFilter.parameter_name)

        if deleted_filter_value == "true":
            actions.update(RESTORE_ACTION)
            actions.update(HARD_DELETE_ACTION)
        elif deleted_filter_value == "false":
            actions.update(SOFT_DELETE_ACTION)
        else:
            actions.update(SOFT_DELETE_ACTION)
            actions.update(RESTORE_ACTION)
            actions.update(HARD_DELETE_ACTION)

        return actions
