import csv
import os
import re

from scaife_viewer.atlas.conf import settings

from ..models import Node, Token


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


def update_version_tokens(version, lookup, refs):
    text_part_urns = [f"{version.urn}{ref}" for ref in refs]
    to_update = []
    tokens = Token.objects.filter(text_part__urn__in=text_part_urns).select_related(
        "text_part"
    )

    fields_to_update = set()
    for token in tokens:
        key = (token.text_part.ref, token.position)
        data = lookup[key]
        update_if_not_set(token, data, fields_to_update)
        to_update.append(token)

    # NOTE: With the PRAGMA directives from SQLite, it ends up being faster to use
    # multiple UPDATE statements within a single transaction rather than use Django's
    # built-in bulk update mechanism
    if fields_to_update and to_update:
        for token in to_update:
            token.save(update_fields=fields_to_update)
    return len(to_update)


def apply_token_annotations():
    """
    @@@ this is just to get the treebank data loaded and queryable;
    want to revisit how this entire extraction works in the future
    """

    paths = get_paths()
    for path in paths:
        lookup, refs = extract_lookup_and_refs(path)
        version = resolve_version(path)
        updated_count = update_version_tokens(version, lookup, refs)
        print(
            f'Updated token annotations [version="{version.urn}" count={updated_count}]'
        )
