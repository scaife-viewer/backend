import csv
import os
from django.conf import settings
from django.db import transaction

from ..models import Node, Token


ANNOTATIONS_DATA_PATH = os.path.join(
    settings.ATLAS_CONFIG["DATA_DIR"], "annotations", "token-annotations"
)


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


def extract_ref_and_position(row):
    """
    @@@ this is just to get the treebank data loaded and queryable;
    want to revisit how this entire extraction works in the future
    """
    text_part_ref, token_idx = row["uuid"][1:].split("_")
    position = int(token_idx) + 1
    return (text_part_ref, position, row)


def extract_lookup_and_refs(path):
    lookup = {}
    refs = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ref, position, data = extract_ref_and_position(row)
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

    # @@@ a better transaction atomic wrapper here maybe?
    print("preparing for bulk update")
    print(len(to_update))
    if fields_to_update and to_update:
        import time
        start = time.time()

        # # BULK_SIZE = int(900 / int(len(fields_to_update)))
        BULK_SIZE = 10000
        for i in range(0, len(to_update), BULK_SIZE):
            subset = to_update[i:i+BULK_SIZE]
            with transaction.atomic(savepoint=False):
                for token in subset:
                    token.save(update_fields=fields_to_update)
        # Token.objects.bulk_update(to_update, fields=fields_to_update, batch_size=500)

        end = time.time()
        print(end-start)

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
