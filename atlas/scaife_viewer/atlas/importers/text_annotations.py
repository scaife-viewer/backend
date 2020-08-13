import json
import os

from django.conf import settings

from ..models import TEXT_ANNOTATION_KIND_SCHOLIA, TextAnnotation


ANNOTATIONS_DATA_PATH = os.path.join(
    settings.ATLAS_CONFIG["DATA_DIR"], "annotations", "text-annotations"
)


def get_paths():
    if not os.path.exists(ANNOTATIONS_DATA_PATH):
        return []
    return [
        os.path.join(ANNOTATIONS_DATA_PATH, f)
        for f in os.listdir(ANNOTATIONS_DATA_PATH)
        if f.endswith(".json")
    ]


def _prepare_text_annotations(path, counters):
    data = json.load(open(path))
    to_create = []
    for row in data:
        urn = row.pop("urn")
        to_create.append(
            TextAnnotation(
                kind=TEXT_ANNOTATION_KIND_SCHOLIA,
                idx=counters["idx"],
                urn=urn,
                data=row,
            )
        )
        counters["idx"] += 1
    return to_create


def import_text_annotations(reset=False):
    if reset:
        TextAnnotation.objects.all().delete()

    to_create = []
    counters = dict(idx=0)
    for path in get_paths():
        to_create.extend(_prepare_text_annotations(path, counters))

    created = len(TextAnnotation.objects.bulk_create(to_create, batch_size=500))
    print(f"Created text annotations [count={created}]")

    for text_annotation in TextAnnotation.objects.all():
        text_annotation.resolve_references()
