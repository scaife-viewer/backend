import json
import logging
from pathlib import Path

import jsonlines
from tqdm import tqdm

from ..hooks import hookset
from ..models import Metadata, Node
from ..utils import chunked_bulk_create


MetadataThroughModel = Metadata.cts_relations.through

logger = logging.getLogger(__name__)


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
    "textgroup": 3,
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


def _field_values(data, values_path):
    field_data = data.get("values", [])
    if isinstance(field_data, list):
        for row in field_data:
            yield row
    elif values_path and field_data.endswith("jsonl"):
        jsonl_path = Path(values_path, field_data)
        with jsonlines.open(jsonl_path) as reader:
            for row in reader.iter():
                yield row
    return []


def _get_visibility(data):
    visibility = data.get("visibility")
    if visibility:
        return visibility
    # TODO: Deprecate the visible flag once Brill
    # has deployed to `2021-07-09-001`
    visible = data.get("visible", None)
    if visible:
        return "reader"
    return "hidden"


def _process_collection(collection, values_path=None):
    # TODO: Throw a warning if not using JSONL / `values_path` and the
    #  number of values crosses an upper threshold
    idx = 0
    to_create = []
    through_lookup = {}
    with tqdm() as pbar:
        for field, data in collection["fields"].items():
            value_count = 0
            for row in _field_values(data, values_path=values_path):
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
                    visibility=_get_visibility(data),
                )
                to_create.append(metadata_obj)
                through_lookup[metadata_obj.urn] = row["cts_urns"]
                value_count += 1
                idx += 1
            pbar.update(value_count)
    return to_create, through_lookup


def _create_metadata(path):
    msg = f"Loading metadata from {path}"
    logger.info(msg)
    collection = json.load(open(path))
    values_path = Path(Path(path).parent, "values")
    objs, through_lookup = _process_collection(collection, values_path=values_path)

    logger.info("Inserting Metadata objects")
    chunked_bulk_create(Metadata, objs)

    logger.info("Generating metadata through models...")
    metadata_qs = Metadata.objects.filter(collection_urn=collection["urn"])
    _resolve_metadata_cts_relations(metadata_qs, through_lookup)


def import_metadata(reset=False):
    if reset:
        Metadata.objects.all().delete()

    metadata_paths = hookset.get_metadata_collection_annotation_paths()
    for path in metadata_paths:
        _create_metadata(path)
