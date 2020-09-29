import json
import os

from scaife_viewer.atlas.conf import settings

from ..models import (
    IMAGE_ANNOTATION_KIND_CANVAS,
    ImageAnnotation,
    ImageROI,
    Node,
)


ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "image-annotations"
)


def get_paths():
    if not os.path.exists(ANNOTATIONS_DATA_PATH):
        return []
    return [
        os.path.join(ANNOTATIONS_DATA_PATH, f)
        for f in os.listdir(ANNOTATIONS_DATA_PATH)
        if f.endswith(".json")
    ]


def _prepare_rois(ia, rois):
    for roi in rois:
        iroi = ImageROI(
            image_annotation=ia,
            data=roi["data"],
            image_identifier=ia.image_identifier,
            coordinates_value=roi["data"]["urn:cite2:hmt:va_dse.v1.imageroi:"]
            .rsplit(":", maxsplit=1)[1]
            .split("@")[1],
        )
        # not using bulk create because of text_parts relation
        iroi.save()
        references = list(Node.objects.filter(urn__in=roi["references"]))
        assert len(references) == len(roi["references"])
        iroi.text_parts.set(references)


def _prepare_image_annotations(path, counters):
    data = json.load(open(path))
    created = []
    for row in data:
        ia = ImageAnnotation(
            kind=IMAGE_ANNOTATION_KIND_CANVAS,
            idx=counters["idx"],
            urn=row["urn"],
            data=row["data"],
            # @@@ hard coded for now, but should change in the future
            canvas_identifier=row["canvas_url"],
            image_identifier=row["image_url"],
        )
        # not using bulk create because of text_parts relation
        ia.save()
        counters["idx"] += 1
        # @@@ we could overload data with references and rois, but am choosing not to
        text_parts = list(Node.objects.filter(urn__in=row["references"]))
        assert len(text_parts) == len(row["references"])
        ia.text_parts.set(text_parts)
        _prepare_rois(ia, row["regions_of_interest"])

        created.append(ia)
    return created


def import_image_annotations(reset=False):
    if reset:
        ImageAnnotation.objects.all().delete()

    created = []
    # @@@ we might want to preserve sequence information if we have it
    counters = dict(idx=0)
    for path in get_paths():
        created.extend(_prepare_image_annotations(path, counters))

    created_count = len(created)
    print(f"Created image annotations [count={created_count}]")
