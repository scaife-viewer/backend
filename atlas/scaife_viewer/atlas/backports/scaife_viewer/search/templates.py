import json

from scaife_viewer.atlas.conf import settings


def text_field_template():
    # TODO: make this opt in
    return {
        "type": "text",
        "fields": {
            "keyword": {
                "ignore_above": 256,
                "type": "keyword",
                "normalizer": "fulltext_normalizer",
            },
        },
        "analyzer": "fulltext_analyzer",
    }


def int_field_template():
    return {
        "type": "integer",
        "coerce": True,
        "ignore_malformed": True,
    }


def date_field_template():
    return {
        "type": "date",
        "format": "year",
    }


def build_fields(collection):
    fields = {}
    for field in collection["fields"]:
        if field["datatype"] == "obj":
            continue
        elif field["datatype"] == "int":
            fields[field["label"]] = int_field_template()
        elif field["datatype"] == "date":
            fields[field["label"]] = date_field_template()
        else:
            # TODO: Handle CITE Obj
            fields[field["label"]] = text_field_template()
    return fields


def get_metadata_fields(collections):
    all_fields = {}
    for collection in collections:
        collection_fields = build_fields(collection)
        # TODO: handle field collisions
        all_fields.update(collection_fields)
    return all_fields


def get_collections():
    from scaife_viewer.atlas.models import Metadata

    collection_urns = Metadata.objects.values_list(
        "collection_urn", flat=True
    ).distinct()
    collections = []
    for collection_urn in collection_urns:
        prefix = collection_urn.rsplit(":", maxsplit=1)[1]
        fields = (
            Metadata.objects.filter(collection_urn=collection_urn)
            .values("label", "datatype", "index")
            .distinct()
        )
        collection_obj = {
            "urn": collection_urn,
            "fields": [
                {"label": f'{prefix}_{field["label"]}', "datatype": field["datatype"]}
                for field in fields
                if field["index"]
            ],
        }
        collections.append(collection_obj)
    return collections


def get_search_template():
    path = settings.SV_ATLAS_SEARCH_TEMPLATE_FIXTURE_PATH
    with open(path) as f:
        template = json.load(f)
    collections = get_collections()
    fields = get_metadata_fields(collections)
    template["mappings"]["text"]["properties"].update(fields)
    return template


# TODO: Backport client callables to ATLAS too
def apply_search_template(es_client, template_name):
    template = get_search_template()
    es_client.indices.delete_template(name=template_name, ignore=[400, 404])
    es_client.indices.put_template(name=template_name, body=template)
