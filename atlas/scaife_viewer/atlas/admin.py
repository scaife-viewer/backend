from django.contrib import admin

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from .models import Node, TextAlignment, TextAlignmentRecord


@admin.register(Node)
class NodeAdmin(TreeAdmin):
    form = movenodeform_factory(Node)


# @@@ re-introduce version and passage filters
@admin.register(TextAlignment)
class TextAlignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "metadata")
    raw_id_fields = ["versions"]
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}


@admin.register(TextAlignmentRecord)
class TextAlignmentRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "citation",
        "idx",
        "alignment",
    )
    list_filter = ("alignment",)
