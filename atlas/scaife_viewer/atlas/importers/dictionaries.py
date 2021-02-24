import json
import os

from scaife_viewer.atlas.conf import settings
from scaife_viewer.atlas.urn import URN

from ..language_utils.grc import normalize_greek_nfkc as normalize_greek
from ..models import Citation, Dictionary, DictionaryEntry, Node, Sense


RESOLVE_CITATIONS_AS_TEXT_PARTS = False

ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "dictionaries",
)


def get_paths(path):
    if not os.path.exists(path):
        return []
    return [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".json")]


def _resolve_citations_as_text_parts(sense, citations):
    # TODO: resolve at least to the highest level we have
    created = []
    idx = 0
    for citation in citations:
        text_part = None
        urn = citation.get("urn")
        if urn:
            urn = URN(urn)
            # TODO: skip a step
            version_urn = urn.up_to(URN.VERSION)
            version_obj = Node.objects.filter(kind="version", urn=version_urn,).first()
            try:
                text_part = (
                    version_obj.get_descendants()
                    .filter(ref=urn.passage.split(".")[0])
                    .get()
                )
            except Node.DoesNotExist:
                print(f"{urn} not found")
        citation_obj = Citation.objects.create(
            label=citation["content"],
            sense=sense,
            data=citation,
            # TODO: proper URNs
            urn=f"{sense.id}-{idx}",
        )
        idx += 1
        if text_part:
            citation_obj.text_parts.add(text_part)
        created.append(citation_obj)
    return created


def _resolve_citations_via_data_urn(sense, citations):
    idx = 0
    to_create = []
    for citation in citations:
        label = f"{sense.id}-{idx}"
        citation_obj = Citation(
            label=label,
            sense=sense,
            data=citation,
            # TODO: proper URNs
            urn=label,
        )
        idx += 1
        to_create.append(citation_obj)
    created = Citation.objects.bulk_create(to_create, batch_size=500)
    return created


def _resolve_citations(senses, citations):
    if RESOLVE_CITATIONS_AS_TEXT_PARTS:
        return _resolve_citations_as_text_parts(senses, citations)
    else:
        # We don't bother checking to see if we can resolve the citation
        # ahead of time (we do this from within LGO currently)
        return _resolve_citations_via_data_urn(senses, citations)


def _process_sense(entry, s, idx, parent=None):
    if parent is None:
        obj = Sense.add_root(
            label=s["label"],
            definition=s["definition"],
            idx=idx,
            urn=s["urn"],
            entry=entry,
        )
    else:
        obj = parent.add_child(
            label=s["label"],
            definition=s["definition"],
            idx=idx,
            urn=s["urn"],
            entry=entry,
        )
    _resolve_citations(obj, s.get("citations", []))
    idx += 1

    for ss in s.get("children", []):
        _process_sense(entry, ss, idx, parent=obj)


def _create_dictionaries(path):
    data = json.load(open(path))
    dictionary = Dictionary.objects.create(label=data["label"], urn=data["urn"],)
    s_idx = 0
    for e_idx, e in enumerate(data["entries"]):
        headword = e["headword"]
        # TODO: Support other languages
        headword_normalized = normalize_greek(headword)
        entry = DictionaryEntry.objects.create(
            headword=headword,
            headword_normalized=headword_normalized,
            idx=e_idx,
            urn=e["urn"],
            dictionary=dictionary,
            data=e.get("data", {}),
        )
        for sense in e["senses"]:
            _process_sense(entry, sense, s_idx, parent=None)


def import_dictionaries(reset=False):
    if reset:
        Dictionary.objects.all().delete()

    dictionary_paths = get_paths(ANNOTATIONS_DATA_PATH)
    for path in dictionary_paths:
        _create_dictionaries(path)
