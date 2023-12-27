import json
import os
from collections import defaultdict

from scaife_viewer.atlas.backports.scaife_viewer.cts.utils import natural_keys
from scaife_viewer.atlas.conf import settings
from scaife_viewer.atlas.urn import URN

from ..models import (
    Node,
    TextAlignment,
    TextAlignmentRecord,
    TextAlignmentRecordRelation,
    Token,
)


ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "text-alignments"
)
RAW_PATH = os.path.join(ANNOTATIONS_DATA_PATH, "raw")


def get_paths():
    if not os.path.exists(ANNOTATIONS_DATA_PATH):
        return []
    return [
        os.path.join(ANNOTATIONS_DATA_PATH, f)
        for f in os.listdir(ANNOTATIONS_DATA_PATH)
        if f.endswith(".json")
    ]


def init_record(versions):
    record = {}
    for version in versions:
        record[version] = []
    return record


def extract_alignment_record_relations(versions, path):
    lookup = defaultdict(lambda: init_record(versions))
    with open(path) as f:
        for line in f:
            if line.startswith("urn:cite2:ducat:alignments.temp:") and line.count(
                "urn:cite2:cite:verbs.v1:aligns"
            ):
                record_urn, _, citation_urn = line.strip().split("#")
                version_urn = URN(citation_urn).up_to(URN.VERSION)
                record = lookup[record_urn]
                record[version_urn].append(citation_urn)
    return lookup


def build_sorted_records(versions, record_relations):
    records = []
    for record_urn, data in record_relations.items():
        relations = []
        for version in versions:
            relation = sorted(data[version], key=natural_keys)
            relations.append(relation)
        # FIXME: Sort key assumes that each relation has tokens
        # or at least the first does
        try:
            sort_key = natural_keys(relations[0][0])
        except Exception as excep:  # noqa: F841
            sort_key = None
        relations = [tuple(r) for r in relations]
        records.append((sort_key, record_urn, tuple(relations)))
    try:
        records = sorted(records, key=lambda x: x[0])
    except Exception as excep:  # noqa: F841
        # FIXME: Handle missing sort key
        records = records
    return records


def set_record_label(record, relation):
    # TODO: Add a record.label field
    if record.metadata.get("label"):
        # TODO: Allow annotation to supply label rather than calculating it
        return
    # TODO: Determine how we want to expose the ve_ref value in terms of addressable
    # tokens; we'll just expose text part ref for now
    tokens = list(relation.tokens.all())
    if not tokens:
        return
    refs = [tokens[0].text_part.ref]
    if tokens[0].text_part_id != tokens[-1].text_part_id:
        refs.append(tokens[-1].text_part.ref)
    record.metadata["label"] = "-".join(refs)


def create_record_relations(record, version_objs, relations):
    first_relation = None
    # TODO: Enforce that relation / version obj is 1:1; determine if we need to
    # support an "empty" relation
    for version_obj, relation in zip(version_objs, relations):
        relation_obj = TextAlignmentRecordRelation(version=version_obj, record=record)
        if first_relation is None:
            first_relation = relation_obj
        relation_obj.save()
        tokens = []
        # TODO: Can we build up a veref map and validate?
        for entry in relation:
            entry_urn = URN(entry)
            ref = entry_urn.passage
            # NOTE: this assumes we're always dealing with a tokenized exemplar, which
            # may not be the case
            text_part_ref, position = ref.rsplit(".", maxsplit=1)
            text_part_urn = f"{version_obj.urn}{text_part_ref}"
            # TODO: compound Q objects query to minimize round trips
            tokens.append(
                Token.objects.get(text_part__urn=text_part_urn, position=position)
            )
        relation_obj.tokens.set(tokens)
    # TODO: review query counts here and some of our SQL hacks

    set_record_label(record, first_relation)


def process_cex(metadata):

    # TODO: Read from metadata; document the format we desire
    # Even the CEX file might need to be inbetween
    # TODO: Better processing of the entire CEX file / CITE model is desired
    versions = metadata["versions"]
    path = os.path.join(RAW_PATH, metadata["filename"])

    record_relations = extract_alignment_record_relations(versions, path)

    records = build_sorted_records(versions, record_relations)

    # # # # # # # # # # # # # # # # # # # # # # # #
    # Create Alignment
    # # # # # # # # # # # # # # # # # # # # # # # #
    # TODO: ordering matters
    version_objs = []
    for version in versions:
        version_objs.append(Node.objects.get(urn=version))

    alignment = TextAlignment(label=metadata["label"], urn=metadata["urn"],)
    alignment.save()
    alignment.versions.set(version_objs)

    # # # # # # # # # # # # # # # # # # # # # # # #
    # Create Record and Relations
    # # # # # # # # # # # # # # # # # # # # # # # #
    idx = 0
    # TODO: review how we might make use of sort key from CEX
    # TODO: sorting versions from Ducat too, especially since Ducat doesn't have 'em
    # maybe something for CITE tools?
    records_to_update = []
    for _, record_urn, relations in records:
        record = TextAlignmentRecord(idx=idx, alignment=alignment, urn=record_urn)
        record.save()
        idx += 1

        create_record_relations(record, version_objs, relations)
        # TODO: Add explicit `label` field
        if record.metadata.get("label"):
            records_to_update.append(record)

    if records_to_update:
        TextAlignmentRecord.objects.bulk_update(records_to_update, fields=["metadata"])


def process_alignments(reset=False):
    if reset:
        TextAlignment.objects.all().delete()

    # TODO: mapper from format to ingestor
    # revisit raw / processed file handling
    # as in Digital Sira
    allowed_formats = ["ducat-cex"]
    created_count = 0
    for path in get_paths():
        try:
            entries = json.load(open(path))
        except Exception as e:
            print(e)
            continue
        else:
            for metadata_entry in entries:
                format_ = metadata_entry.get("format", "unknown")
                if format_ not in allowed_formats:
                    raise NotImplementedError(
                        f"Cannot parse annotation format: {format_}"
                    )
                process_cex(metadata_entry)
                created_count += 1
    print(f"Alignments created: {created_count}")
