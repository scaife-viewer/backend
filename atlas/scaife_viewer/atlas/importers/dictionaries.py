import json
import logging
import os
from collections import defaultdict

from tqdm import tqdm

from scaife_viewer.atlas.conf import settings

from ..language_utils import normalize_string
from ..models import Citation, Dictionary, DictionaryEntry, Node, Sense
from ..utils import chunked_bulk_create


# FIXME: Factor out globals into a dictionary-level attr
ROOT_PATH_LOOKUP = []
PARENT_PATH_LOOKUP = defaultdict(dict)
PATH_SET = set()

CitationThroughModel = Citation.text_parts.through
RESOLVE_CITATIONS_AS_TEXT_PARTS = True

ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "dictionaries",
)

logger = logging.getLogger(__name__)


def get_paths(path):
    if not os.path.exists(path):
        return []
    return [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".json")]


def _prepare_citation_objs(lookup_dict, citations):
    idx = 0
    to_create = []
    for citation in citations:
        citation_obj = Citation(
            label=citation.get("ref", ""),
            # sense=sense,
            data=citation["data"],
            urn=citation["urn"],
            idx=idx,
        )
        # FIXME: This is a bit hacky; we likely want a parallel data structure
        # that passes FKs for "deferred" purposes
        citation_obj.entry_urn = lookup_dict.get("entry_urn")
        citation_obj.sense_urn = lookup_dict.get("sense_urn")
        idx += 1
        to_create.append(citation_obj)
    return to_create


def _process_sense(entry, s, idx, parent=None, last_sibling=None):
    senses = []
    citations = []
    if parent is None:
        if ROOT_PATH_LOOKUP:
            last_root = ROOT_PATH_LOOKUP.pop()
            path = last_root._inc_path()
        else:
            path = Sense._get_path(None, 1, 1)
        obj = Sense(
            label=s["label"],
            definition=s["definition"],
            idx=idx,
            urn=s["urn"],
            depth=1,
            path=path,
        )
        assert path not in PATH_SET
        ROOT_PATH_LOOKUP.append(obj)
    else:
        path = None
        depth = parent.depth + 1
        if last_sibling:
            last_sibling = last_sibling[0]
            if last_sibling.path == parent.path:
                logger.debug("this is the first child of the parent")
                path = Sense._get_path(parent.path, depth, 1)
                assert path not in PATH_SET
                PARENT_PATH_LOOKUP[parent.path].update({depth: path})
            elif last_sibling.depth == depth:
                logger.debug("this is a sibling at the current depth")
                path = last_sibling._inc_path()
                assert path not in PATH_SET
                PARENT_PATH_LOOKUP[parent.path].update({depth: path})
            elif last_sibling.depth > depth:
                logger.debug("this is a node at a higher depth")
                last_sibling_path = PARENT_PATH_LOOKUP[parent.path][depth]
                sibling_obj = Sense(depth=depth, path=last_sibling_path)
                path = sibling_obj._inc_path()
                PARENT_PATH_LOOKUP[parent.path].update({depth: path})
                # last_seen_path = PARENT_PATH_LOOKUP[parent.path][depth]
                # path = Sense._get_path(last_seen_path, depth, 1)
                # this
            else:
                assert False
        else:
            assert False
        logger.debug(path)
        obj = Sense(
            label=s["label"],
            definition=s["definition"],
            idx=idx,
            urn=s["urn"],
            depth=depth,
            path=path,
            # entry=entry,
        )
        assert path is not None
        PATH_SET.add(obj.path)

    senses.append(obj)

    citations.extend(
        _prepare_citation_objs(
            dict(entry_urn=entry.urn, sense_urn=obj.urn), s.get("citations", [])
        )
    )
    idx += 1

    for ss in s.get("children", []):
        new_senses, new_citations = _process_sense(
            entry, ss, idx, parent=obj, last_sibling=senses[-1:]
        )
        senses.extend(new_senses)
        citations.extend(new_citations)
    return senses, citations


def _bulk_prepare_citation_through_objects(qs):
    logger.info("Retrieving URNs for citations")
    citation_urn_pk_values = qs.values_list("data__urn", "pk")

    candidates = list(set([c[0] for c in citation_urn_pk_values]))
    msg = f"URNs retrieved: {len(candidates)}"
    logger.info(msg)

    logger.info("Building URN to Node (TextPart) pk lookup")
    node_urn_pk_values = Node.objects.filter(urn__in=candidates).values_list(
        "urn", "pk"
    )
    text_part_lookup = {}
    for urn, pk in node_urn_pk_values:
        text_part_lookup[urn] = pk

    logger.info("Preparing through objects for insert")
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
    logger.info(msg)

    chunked_bulk_create(CitationThroughModel, prepared_objs)


def _defer_entry(deferred, entry, data, s_idx):
    """
    Create entry and related child objects in memory, but don't yet
    persist them to the database.

    This avoids an avalanche of SQL SELECT and INSERT statements that
    would otherwise occur on each `.create` or `.save` call.
    """
    senses = []
    citations = []
    citations.extend(
        _prepare_citation_objs(dict(entry_urn=entry.urn), data.get("citations", []))
    )
    for sense in data["senses"]:
        new_senses, new_citations = _process_sense(entry, sense, s_idx, parent=None)
        senses.extend(new_senses)
        citations.extend(new_citations)
    deferred["entries"].append(entry)
    deferred["senses"].append(senses)
    deferred["citations"].append(citations)


def _create_dictionaries(path):
    # TODO: Prefer JSONL spec to avoid memory headaches
    msg = f"Loading dictionary from {path}"
    logger.info(msg)
    data = json.load(open(path))
    dictionary = Dictionary.objects.create(label=data["label"], urn=data["urn"],)
    s_idx = 0
    entry_count = len(data["entries"])
    deferred = defaultdict(list)

    logger.info("Extracting entries, senses and citations")
    with tqdm(total=entry_count) as pbar:
        for e_idx, e in enumerate(data["entries"]):
            pbar.update(1)
            headword = e["headword"]
            headword_normalized = normalize_string(headword)
            entry = DictionaryEntry(
                headword=headword,
                headword_normalized=headword_normalized,
                idx=e_idx,
                urn=e["urn"],
                dictionary=dictionary,
                data=e.get("data", {}),
            )
            # FIXME: Ensure `s_idx` is actually getting incremented
            _defer_entry(deferred, entry, e, s_idx)

    logger.info("Inserting DictionaryEntry objects")
    chunked_bulk_create(DictionaryEntry, deferred["entries"])

    logger.info("Setting entry_id on Sense objects")
    entry_urn_pk_lookup = {}
    entry_urn_pk_lookup.update(
        DictionaryEntry.objects.filter(dictionary_id=dictionary.id)
        .order_by("pk")
        .values_list("urn", "pk")
    )

    entry_ids = entry_urn_pk_lookup.values()
    for entry_id, entry_senses in zip(entry_ids, deferred["senses"]):
        for s in entry_senses:
            s.entry_id = entry_id

    import itertools

    logger.info("Inserting Sense objects")
    chunked_bulk_create(Sense, itertools.chain.from_iterable(deferred["senses"]))

    logger.info("Setting sense_id on Citation objects")
    sense_urn_pk_lookup = {}
    sense_urn_pk_lookup.update(
        Sense.objects.filter(entry__dictionary_id=dictionary.id).values_list(
            "urn", "pk"
        )
    )
    for citations in deferred["citations"]:
        for citation in citations:
            entry_id = entry_urn_pk_lookup.get(citation.entry_urn, None)
            citation.entry_id = entry_id
            sense_id = sense_urn_pk_lookup.get(citation.sense_urn, None)
            citation.sense_id = sense_id

    logger.info("Inserting Citation objects")
    chunked_bulk_create(Citation, itertools.chain.from_iterable(deferred["citations"]))

    if RESOLVE_CITATIONS_AS_TEXT_PARTS:
        logger.info("Generating citation through models...")
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
