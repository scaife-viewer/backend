import csv
import os

from django.conf import settings

import logfmt

from ..models import NamedEntity, Node


NAMED_ENTITIES_DATA_PATH = os.path.join(
    settings.ATLAS_CONFIG["DATA_DIR"], "annotations", "named-entities"
)
ENTITIES_DIR = os.path.join(NAMED_ENTITIES_DATA_PATH, "processed", "entities")
STANDOFF_DIR = os.path.join(NAMED_ENTITIES_DATA_PATH, "processed", "standoff")


def get_entity_paths():
    if not os.path.exists(ENTITIES_DIR):
        return []
    return [
        os.path.join(ENTITIES_DIR, f)
        for f in os.listdir(ENTITIES_DIR)
        if f.endswith(".csv")
    ]


def _populate_lookup(path, lookup):
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            urn = row["urn"]
            kind = "person" if urn.count("pers") > 0 else "place"
            data = next(logfmt.parse([row.get("data", "")]), dict())
            named_entity, _ = NamedEntity.objects.get_or_create(
                urn=urn,
                defaults={
                    "title": row["label"],
                    "description": row["description"],
                    "url": row["link"],
                    "kind": kind,
                    "data": data,
                },
            )
            lookup[named_entity.urn] = named_entity


def get_standoff_paths():
    if not os.path.exists(STANDOFF_DIR):
        return []
    return [
        os.path.join(STANDOFF_DIR, f)
        for f in os.listdir(STANDOFF_DIR)
        if f.endswith(".csv")
    ]


def _apply_entities(path, lookup):
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            named_entity = lookup[row["named_entity_urn"]]
            text_part = Node.objects.get(urn=row["ref"])
            position = int(row["token_position"])
            tokens = text_part.tokens.filter(position__in=[position])
            named_entity.tokens.add(*tokens)


def apply_named_entities(reset=True):
    if reset:
        NamedEntity.objects.all().delete()

    lookup = {}
    for path in get_entity_paths():
        _populate_lookup(path, lookup)

    for path in get_standoff_paths():
        _apply_entities(path, lookup)
