import csv
import os
import re

from scaife_viewer.atlas.conf import settings

from ..models import Node, Token, TokenAnnotation, TokenAnnotationCollection


ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "token-annotations"
)


VE_REF_PATTTERN = re.compile(r"(?P<ref>.*).t(?P<token>.*)")


def get_paths():
    if not os.path.exists(ANNOTATIONS_DATA_PATH):
        return []
    return [
        os.path.join(ANNOTATIONS_DATA_PATH, f)
        for f in os.listdir(ANNOTATIONS_DATA_PATH)
        if f.endswith(".csv")
    ]


def resolve_version(path):
    versionish = f'{os.path.basename(path).split(".csv")[0]}:'
    return Node.objects.filter(urn__endswith=versionish).get()


def extract_ref_and_token_position(row):
    match = VE_REF_PATTTERN.match(row["ve_ref"])
    assert match
    return (match["ref"], int(match["token"]), row)


def extract_lookup_and_refs(path):
    lookup = {}
    refs = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ref, position, data = extract_ref_and_token_position(row)
            key = (ref, position)
            refs.append(ref)
            lookup[key] = data
    return lookup, refs


def update_if_not_set(token, data, fields_to_update):
    for k, v in data.items():
        if hasattr(token, k) and not getattr(token, k):
            setattr(token, k, v)
            fields_to_update.add(k)


def create_token_annotations(collection, version, lookup, refs):
    # TODO: Relying on an "upsert" for annotations; likely we can
    # optimize this further
    text_part_urns = [f"{version.urn}{ref}" for ref in refs]
    tokens = Token.objects.filter(text_part__urn__in=text_part_urns).select_related(
        "text_part"
    )

    to_create = []
    for token in tokens:
        # TODO: Update if not set was assuming we would have fields that could get clobbered; no longer true!
        key = (token.text_part.ref, token.position)
        data = lookup[key]

        if not data:
            continue

        to_create.append(
            TokenAnnotation(token=token, data=data, collection=collection,)
        )
    return len(TokenAnnotation.objects.bulk_create(to_create))


def apply_token_annotations(reset=True):
    """
    @@@ this is just to get the treebank data loaded and queryable;
    want to revisit how this entire extraction works in the future
    """

    paths = get_paths()
    for path in paths:
        lookup, refs = extract_lookup_and_refs(path)
        version = resolve_version(path)

        # FIXME: Update annotations in data repos to v2 format
        collection_urn = "urn:cite2:beyond-tranlsation:token_annotation_collection.atlas_v1:il_1_crane_shamsian"
        if reset:
            TokenAnnotationCollection.objects.filter(urn=collection_urn).delete()

        # TODO: Set attribution information
        collection = TokenAnnotationCollection.objects.create(
            urn=collection_urn, label="Iliad Annotations", metadata={}
        )
        annotations_count = create_token_annotations(collection, version, lookup, refs)
        print(
            f'Created token annotations [version="{version.urn}" count={annotations_count}]'
        )
