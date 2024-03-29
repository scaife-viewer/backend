import csv
import os
import re

import yaml

from ..hooks import hookset
from ..models import Node, Token, TokenAnnotation, TokenAnnotationCollection

VE_REF_PATTTERN = re.compile(r"(?P<ref>.*).t(?P<token>.*)")


def resolve_version(path):
    versionish = f'{os.path.basename(path).split(".csv")[0]}:'
    version_obj = Node.objects.filter(urn__endswith=versionish).first()
    if not version_obj:
        print(f'Could not resolve version for {path.name} [urn="{versionish}"]')
    return version_obj


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

        # TODO: Add further error logging for this
        try:
            data = lookup[key]
        except KeyError:
            data = None

        if not data:
            continue

        to_create.append(
            TokenAnnotation(
                token=token,
                data=data,
                collection=collection,
            )
        )
    return len(TokenAnnotation.objects.bulk_create(to_create))


def apply_token_annotations(reset=True):
    """
    @@@ this is just to get the treebank data loaded and queryable;
    want to revisit how this entire extraction works in the future
    """

    paths = hookset.get_token_annotation_paths()
    for path in paths:
        metadata_path = path / "metadata.yml"
        collection = yaml.safe_load(metadata_path.open())

        if reset:
            TokenAnnotationCollection.objects.filter(urn=collection["urn"]).delete()

        # TODO: Standardize use of `values` for ATLAS files
        values = collection.get("values")
        if not values or not values.endswith("csv"):
            continue

        values_path = path / values
        lookup, refs = extract_lookup_and_refs(values_path)
        # TODO: Move this to metadata and or values
        version = resolve_version(values_path)
        if not version:
            continue

        # TODO: Set attribution information
        metadata = collection.pop("metadata", {})
        collection_obj = TokenAnnotationCollection.objects.create(
            urn=collection["urn"], label=collection["label"], metadata=metadata
        )
        annotations_count = create_token_annotations(
            collection_obj, version, lookup, refs
        )
        print(
            f'Created token annotations [version="{version.urn}" count={annotations_count}]'
        )
