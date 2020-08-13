from django.contrib import admin

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from .models import Node, TextAlignment, TextAlignmentChunk


@admin.register(Node)
class NodeAdmin(TreeAdmin):
    form = movenodeform_factory(Node)


@admin.register(TextAlignment)
class TextAlignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "metadata", "version")
    list_filter = ("version",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ["name"]}


@admin.register(TextAlignmentChunk)
class TextAlignmentChunkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "citation",
        "metadata",
        "idx",
        "version",
        "alignment",
        "start",
        "end",
    )
    list_filter = ("version", "alignment")
    raw_id_fields = ("start", "end", "version")
