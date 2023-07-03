import json
from pathlib import Path

from scaife_viewer.atlas.conf import settings
from scaife_viewer.atlas.models import TOCEntry


ANNOTATIONS_DATA_PATH = Path(settings.SV_ATLAS_DATA_DIR) / "annotations" / "tocs"


def get_paths():
    if not ANNOTATIONS_DATA_PATH.exists():
        return []
    for dirpath in ANNOTATIONS_DATA_PATH.iterdir():
        if not dirpath.is_dir():
            continue
        for path in dirpath.iterdir():
            if path.suffix == ".json":
                yield path


def add_descendants(parent, children):
    # TODO: Bulkify
    for pos, item in enumerate(children):
        uri = item["uri"]
        urn = item.get("@id")
        if urn is None:
            urn = f"{parent.urn}:{pos}"
        # TODO: Distinguish between title in the parent
        # and title for the child; Iliad folios in particular;
        # Probably YAGNI with proper breadcrumb support...
        child = parent.add_child(
            urn=urn,
            uri=uri,
            label=item.get("title", uri),
            description=item.get("description", ""),
        )
        grandchildren = item.get("items")
        if grandchildren:
            add_descendants(child, grandchildren)


def process_tocs(reset=True):
    if reset:
        TOCEntry.objects.all().delete()

    for path in get_paths():
        with path.open() as f:
            data = json.load(f)
        print(f"Processing {path.name}")
        root = TOCEntry.add_root(
            urn=data.get("@id"),
            label=data.get("title"),
            description=data.get("description"),
            uri=data.get("@id"),
        )
        children = data.get("items")
        if children:
            add_descendants(root, children)
        created_count = root.get_descendant_count() + 1
        print(f"Entries created: {created_count}")
