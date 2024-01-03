import json
from collections import defaultdict
from pathlib import Path

from scaife_viewer.atlas.conf import settings
from scaife_viewer.atlas.models import Node, TOCEntry
from scaife_viewer.atlas.urn import URN
from scaife_viewer.atlas.utils import chunked_bulk_create


ANNOTATIONS_DATA_PATH = Path(settings.SV_ATLAS_DATA_DIR) / "annotations" / "tocs"

CTSThroughModel = TOCEntry.cts_relations.through


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


def link_tocs(reset=True):
    """
    Link TOCs to their passages
    """
    if reset:
        CTSThroughModel.objects.all().delete()

    print("Linking TOCs to works")
    # Initially, we'll just resolve the top-level TOC to works
    work_to_paths_lu = defaultdict(set)
    path_uris = TOCEntry.objects.filter(uri__startswith="urn:cts").values_list(
        "path", "uri"
    )
    unique_paths = set()
    for path, uri in path_uris:
        work_urn = URN(uri).up_to(URN.WORK)
        top_level_path = path[0:4]
        unique_paths.add(top_level_path)
        work_to_paths_lu[work_urn].add(top_level_path)

    top_level_tocs = TOCEntry.objects.filter(path__in=unique_paths)
    top_level_path_to_id_lu = {}
    for path, id in top_level_tocs.values_list("path", "id"):
        top_level_path_to_id_lu[path] = id

    to_create = []
    for work in Node.objects.filter(urn__in=work_to_paths_lu):
        for path in work_to_paths_lu[work.urn]:
            to_create.append(
                CTSThroughModel(
                    node_id=work.id, tocentry_id=top_level_path_to_id_lu[path],
                )
            )
    chunked_bulk_create(CTSThroughModel, to_create)


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

    link_tocs(reset=reset)
