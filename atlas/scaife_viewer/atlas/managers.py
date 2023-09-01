from django.db import models


class NodeManager(models.Manager):
    """
    Overrides MP_NodeManager's custom delete method.

    This is needed because we aren't setting `numchild`, so
    the custom delete method fails.

    FIXME: Remove overrides
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.order_by("path")
