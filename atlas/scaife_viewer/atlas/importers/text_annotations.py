import json
import logging

import jsonlines

# FIXME: Hooksets
from ..constants import (
    TEXT_ANNOTATION_KIND_SCHOLIA,
    TEXT_ANNOTATION_KIND_SYNTAX_TREE,
    TEXT_ANNOTATION_KIND_COMMENTARY,
)
from ..hooks import hookset
from ..models import Node, TextAnnotation
from ..utils import chunked_bulk_create


logger = logging.getLogger(__name__)

TextAnnotationThroughModel = TextAnnotation.text_parts.through


def load_data(path):
    if path.suffix == ".jsonl":
        with jsonlines.open(path) as reader:
            for row in reader.iter():
                yield row
    else:
        data = json.load(path.open())
        for row in data:
            yield row


def _prepare_text_annotations(path, counters, kind):
    to_create = []
    for row in load_data(path):
        urn = row.pop("urn")
        to_create.append(
            TextAnnotation(kind=kind, idx=counters["idx"], urn=urn, data=row,)
        )
        counters["idx"] += 1
    return to_create


# TODO: Determine if we want some of these bulk methods to move to a classmethod
def _bulk_prepare_text_annotation_through_objects(qs):
    logger.info("Extracting URNs from text annotation references")
    qs_with_references = qs.exclude(data__references=None)
    through_lookup = {}
    through_values = qs_with_references.values("id", "data__references")
    urns = set()
    for row in through_values:
        through_lookup[row["id"]] = row["data__references"]
        urns.update(row["data__references"])
    msg = f"URNs extracted: {len(urns)}"
    logger.info(msg)

    logger.info("Building URN to Node pk lookup")
    node_urn_pk_values = Node.objects.filter(urn__in=urns).values_list("urn", "pk")
    node_lookup = {}
    for urn, pk in node_urn_pk_values:
        node_lookup[urn] = pk

    logger.info("Preparing through objects for insert")
    to_create = []
    for textannotation_id, urns in through_lookup.items():
        for urn in urns:
            # TODO: Remove this lookup fallback
            node_id = node_lookup.get(urn, None)
            if node_id:
                to_create.append(
                    TextAnnotationThroughModel(
                        node_id=node_id, textannotation_id=textannotation_id
                    )
                )
    return to_create


def _resolve_text_annotation_text_parts(qs):
    prepared_objs = _bulk_prepare_text_annotation_through_objects(qs)

    relation_label = TextAnnotationThroughModel._meta.verbose_name_plural
    msg = f"Bulk creating {relation_label}"
    logger.info(msg)

    chunked_bulk_create(TextAnnotationThroughModel, prepared_objs)


# TODO: Break this part into individual pipelines
def import_text_annotations(reset=False):
    if reset:
        TextAnnotation.objects.all().delete()

    to_create = []
    counters = dict(idx=0)

    # FIXME: hooksets for generic text annotations
    scholia_annotation_paths = hookset.get_text_annotation_paths()
    for path in scholia_annotation_paths:
        to_create.extend(
            _prepare_text_annotations(path, counters, kind=TEXT_ANNOTATION_KIND_SCHOLIA)
        )

    commentary_annotation_paths = hookset.get_commentary_annotation_paths()
    for path in commentary_annotation_paths:
        to_create.extend(
            _prepare_text_annotations(
                path, counters, kind=TEXT_ANNOTATION_KIND_COMMENTARY
            )
        )

    syntax_tree_annotation_paths = hookset.get_syntax_tree_annotation_paths()
    for path in syntax_tree_annotation_paths:
        to_create.extend(
            _prepare_text_annotations(
                path, counters, kind=TEXT_ANNOTATION_KIND_SYNTAX_TREE
            )
        )

    logger.info("Inserting TextAnnotation objects")
    chunked_bulk_create(TextAnnotation, to_create)

    logger.info("Generating TextAnnotation through models...")
    _resolve_text_annotation_text_parts(TextAnnotation.objects.all())
