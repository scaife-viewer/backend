import json
import os

from tqdm import tqdm

from scaife_viewer.atlas.conf import settings

from ..language_utils import normalize_string
from ..models import Citation, Dictionary, DictionaryEntry, Node, Sense
from ..utils import chunked_bulk_create


CitationThroughModel = Citation.text_parts.through
RESOLVE_CITATIONS_AS_TEXT_PARTS = True

ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "dictionaries",
)


def get_paths(path):
    if not os.path.exists(path):
        return []
    return [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".json")]


def _bulk_create_citations(sense, citations):
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
    # TODO: Defer creation to reduce SQL inserts in a
    # nested loop
    return created


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
    _bulk_create_citations(obj, s.get("citations", []))
    idx += 1

    for ss in s.get("children", []):
        _process_sense(entry, ss, idx, parent=obj)


def _bulk_prepare_citation_through_objects(qs):
    msg = "Retrieving URNs for citations"
    print(msg)
    citation_urn_pk_values = qs.values_list("data__urn", "pk")

    candidates = list(set([c[0] for c in citation_urn_pk_values]))
    msg = f"URNs retrieved: {len(candidates)}"
    print(msg)

    msg = "Building URN to Node (TextPart) pk lookup"
    print(msg)
    node_urn_pk_values = Node.objects.filter(urn__in=candidates).values_list(
        "urn", "pk"
    )
    text_part_lookup = {}
    for urn, pk in node_urn_pk_values:
        text_part_lookup[urn] = pk

    msg = "Preparing through objects for insert"
    print(msg)
    to_create = []
    for urn, citation_id in citation_urn_pk_values:
        node_id = text_part_lookup.get(urn, None)
        if node_id:
            to_create.append(
                CitationThroughModel(node_id=node_id, citation_id=citation_id)
            )
    return to_create


def _resolve_citation_textparts(qs):
    prepared_objs = _bulk_prepare_citation_through_objects(qs)

    relation_label = CitationThroughModel._meta.verbose_name_plural
    msg = f"Bulk creating {relation_label}"
    print(msg)

    chunked_bulk_create(CitationThroughModel, prepared_objs)


def _create_dictionaries(path):
    data = json.load(open(path))
    dictionary = Dictionary.objects.create(label=data["label"], urn=data["urn"],)
    s_idx = 0
    entry_count = len(data["entries"])
    with tqdm(total=entry_count) as pbar:
        for e_idx, e in enumerate(data["entries"]):
            pbar.update(1)
            headword = e["headword"]
            headword_normalized = normalize_string(headword)
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

    if RESOLVE_CITATIONS_AS_TEXT_PARTS:
        msg = "Generating citation through models..."
        print(msg)
        citations_with_urns = Citation.objects.filter(
            sense__entry__dictionary=dictionary
        ).exclude(data__urn=None)
        _resolve_citation_textparts(citations_with_urns)


def import_dictionaries(reset=False):
    if reset:
        Dictionary.objects.all().delete()

    dictionary_paths = get_paths(ANNOTATIONS_DATA_PATH)
    for path in dictionary_paths:
        _create_dictionaries(path)
