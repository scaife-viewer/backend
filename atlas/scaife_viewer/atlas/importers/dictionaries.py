import json
import os

from scaife_viewer.atlas.conf import settings

from ..models import Dictionary, DictionaryEntry, Node, Sense


ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR,
    "annotations",
    "dictionaries",
)


def get_paths(path):
    if not os.path.exists(path):
        return []
    return [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".json")]


def _resolve_citations(citations):
    urns = []
    for citation in citations:
        workpart, ref = citation.split(":")
        version_obj = Node.objects.filter(
            kind="version", urn__contains=workpart
        ).first()
        citation_urn = f"{version_obj.urn}{ref.split('.')[0]}"
        try:
            urns.append(
                Node.objects.filter(urn=f"{version_obj.urn}{ref.split('.')[0]}").get()
            )
        except Node.DoesNotExist:
            print(f"{citation_urn} not found")
    return list(set(urns))


def _create_dictionaries(path, counters, kind):
    data = json.load(open(path))
    dictionary = Dictionary.objects.create(label=data["label"], urn=data["urn"],)
    s_idx = 0
    for e_idx, e in enumerate(data["entries"]):
        entry = DictionaryEntry.objects.create(
            headword=e["headword"], idx=e_idx, urn=e["urn"], dictionary=dictionary
        )
        for s in e["senses"]:
            sense = Sense.add_root(
                label=s["label"],
                definition=s["definition"],
                idx=s_idx,
                urn=s["urn"],
                entry=entry,
            )
            sense.citations.set(_resolve_citations(s.get("citations", [])))
            s_idx += 1
            for ss in s.get("subsenses", []):
                subsense = sense.add_child(
                    label=ss["label"],
                    definition=ss["definition"],
                    idx=s_idx,
                    urn=ss["urn"],
                    entry=entry,
                )
                subsense.citations.set(_resolve_citations(ss.get("citations", [])))
                s_idx += 1


def import_dictionaries(reset=False):
    if reset:
        Dictionary.objects.all().delete()

    dictionary_paths = get_paths(ANNOTATIONS_DATA_PATH)
    for path in dictionary_paths:
        _create_dictionaries(path)
