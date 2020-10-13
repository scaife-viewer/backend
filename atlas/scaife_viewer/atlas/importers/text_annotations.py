import json
import os

from scaife_viewer.atlas.conf import settings

from ..models import (
    TEXT_ANNOTATION_KIND_SCHOLIA,
    TEXT_ANNOTATION_KIND_SYNTAX_TREE,
    TextAnnotation,
)


ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "text-annotations"
)
SYNTAX_TREES_ANNOTATIONS_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "syntax-trees"
)


def get_paths(path):
    if not os.path.exists(path):
        return []
    return [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".json")]


def _prepare_text_annotations(path, counters, kind):
    data = json.load(open(path))
    to_create = []
    for row in data:
        urn = row.pop("urn")
        to_create.append(
            TextAnnotation(kind=kind, idx=counters["idx"], urn=urn, data=row,)
        )
        counters["idx"] += 1
    return to_create


def import_text_annotations(reset=False):
    if reset:
        TextAnnotation.objects.all().delete()

    to_create = []
    counters = dict(idx=0)

    scholia_annotation_paths = get_paths(ANNOTATIONS_DATA_PATH)
    for path in scholia_annotation_paths:
        to_create.extend(
            _prepare_text_annotations(path, counters, kind=TEXT_ANNOTATION_KIND_SCHOLIA)
        )

    syntax_tree_annotation_paths = get_paths(SYNTAX_TREES_ANNOTATIONS_PATH)
    for path in syntax_tree_annotation_paths:
        to_create.extend(
            _prepare_text_annotations(
                path, counters, kind=TEXT_ANNOTATION_KIND_SYNTAX_TREE
            )
        )

    created = len(TextAnnotation.objects.bulk_create(to_create, batch_size=500))
    print(f"Created text annotations [count={created}]")

    for text_annotation in TextAnnotation.objects.all():
        text_annotation.resolve_references()
