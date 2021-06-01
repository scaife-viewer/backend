import json
import logging
import os

from tqdm import tqdm

from scaife_viewer.atlas.conf import settings

from ..models import Metadata, Node
from ..utils import chunked_bulk_create


MetadataThroughModel = Metadata.cts_relations.through

ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "structured-metadata",
)

logger = logging.getLogger(__name__)


def get_paths(path):
    if not os.path.exists(path):
        return []
    return [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".json")]


def _bulk_prepare_metadata_through_objects(qs, through_lookup):
    logger.info("Extracting URNs for metadata")

    urns = []
    for value in through_lookup.values():
        urns.extend(value)
    urns = list(set(urns))
    msg = f"URNs extracted: {len(urns)}"
    logger.info(msg)

    urn_id_values = qs.values_list("urn", "id")

    logger.info("Building URN to Node pk lookup")
    node_urn_pk_values = Node.objects.filter(urn__in=urns).values_list("urn", "pk")
    node_lookup = {}
    for urn, pk in node_urn_pk_values:
        node_lookup[urn] = pk

    logger.info("Preparing through objects for insert")
    to_create = []
    for metadata_urn, metadata_id in urn_id_values:
        urns = through_lookup.get(metadata_urn, [])
        for urn in urns:
            node_id = node_lookup.get(urn, None)
            if node_id:
                to_create.append(
                    MetadataThroughModel(node_id=node_id, metadata_id=metadata_id)
                )
    return to_create


def _resolve_metadata_cts_relations(qs, through_lookup):
    prepared_objs = _bulk_prepare_metadata_through_objects(qs, through_lookup)

    relation_label = MetadataThroughModel._meta.verbose_name_plural
    msg = f"Bulk creating {relation_label}"
    logger.info(msg)

    chunked_bulk_create(MetadataThroughModel, prepared_objs)


# FIXME: Standardize these depths and make the GraphQL filters
# take them into account
UP_TO_DEPTHS = {
    "work": 4,
    "version": 5,
    # TODO: Prefer citation-level, which could be nodes >= 6;
    # we may end up just doing those types of queries for "depth"
    # in our references filters
    "passage": 6,
}


def _value_fields(kind, row):
    if kind == "obj":
        value = ""
        value_obj = row["value_obj"]
    else:
        value = row["value"]
        # TODO: None?
        value_obj = {}
    return (value, value_obj)


def _process_collection(collection):
    idx = 0
    to_create = []
    through_lookup = {}
    with tqdm() as pbar:
        for field, data in collection["fields"].items():
            value_count = 0
            for row in data["values"]:
                value, value_obj = _value_fields(data["kind"], row)
                metadata_obj = Metadata(
                    urn=row["urn"],
                    # TODO: Wither idx?
                    idx=idx,
                    # TODO: ElasticSearch mapping?
                    datatype=data["kind"],
                    collection_urn=collection["urn"],
                    label=field,
                    value=value,
                    value_obj=value_obj,
                    # TODO actually get the depth
                    depth=UP_TO_DEPTHS[data["up_to"]],
                    index=data["index"],
                    visible=data["visible"],
                )
                to_create.append(metadata_obj)
                through_lookup[metadata_obj.urn] = row["cts_urns"]
                value_count += 1
                idx += 1
            pbar.update(value_count)
    return to_create, through_lookup


def _create_metadata(path):
    # TODO: Prefer JSONL spec to avoid memory headaches
    msg = f"Loading metadata from {path}"
    logger.info(msg)
    collection = json.load(open(path))
    objs, through_lookup = _process_collection(collection)

    logger.info("Inserting Metadata objects")
    chunked_bulk_create(Metadata, objs)

    logger.info("Generating metadata through models...")
    metadata_qs = Metadata.objects.filter(collection_urn=collection["urn"])
    _resolve_metadata_cts_relations(metadata_qs, through_lookup)


def import_metadata(reset=False):
    if reset:
        Metadata.objects.all().delete()

    metadata_paths = get_paths(ANNOTATIONS_DATA_PATH)
    for path in metadata_paths:
        _create_metadata(path)
