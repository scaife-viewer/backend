import csv
import json
import os
import re

from django.conf import settings
from django.db import transaction

from ..models import Node, TextAlignment, TextAlignmentChunk


ALIGNMENTS_DATA_PATH = os.path.join(settings.ATLAS_CONFIG["DATA_DIR"], "alignments")
ALIGNMENTS_METADATA_PATH = os.path.join(ALIGNMENTS_DATA_PATH, "metadata.json")

LINE_KIND_UNKNOWN = None
LINE_KIND_NEW = "new"
LINE_KIND_CONTINUES = "continues"
LINE_KIND_CONTINUATION = "continuation"

CITATION_REFERENCE_REGEX = re.compile(r"\d+\.\d+")
CONTENT_REFERENCE_REGEX = re.compile(r"\[\d+\.\d+\]")
CONTENT_FOOTNOTE_REGEX = re.compile(r"\[\d+\]")


def get_citation(greek_content):
    """
    Extracts citation from Greek content.

    The `citation` field in the CSV contains inaccuracies,
    so we'll build the citation field ourselves.
    """
    refs = CITATION_REFERENCE_REGEX.findall(greek_content)
    start = refs[0]
    end = refs[-1]
    if start == end:
        return start
    else:
        return "-".join([start, end])


def transform_greek_content(greek_content):
    """
    Removes reference headings and footnote markers from
    the milestone's Greek content.
    """
    greek_content = CONTENT_FOOTNOTE_REGEX.sub("", greek_content)
    references = CONTENT_REFERENCE_REGEX.findall(greek_content)
    tokens = [v for v in greek_content.split(" ") if v]
    content = []
    for pos, reference in enumerate(references):
        ref_idx = tokens.index(reference)
        try:
            next_idx = tokens.index(references[pos + 1])
        except IndexError:
            subset = tokens[ref_idx:]
        else:
            subset = tokens[ref_idx:next_idx]
        ref_label = CITATION_REFERENCE_REGEX.findall(subset.pop(0))[0]
        content.append((ref_label, " ".join(subset)))
    return content


def map_leaves_to_milestones(leaves_to_milestones_lu, milestone_id, pos, leaves):
    """
    Updates the `LEAVES_TO_MILESTONES` index with each
    reference within a given citation.
    """
    for reference, text in leaves:
        leaves_to_milestones_lu.setdefault(reference, []).append(pos)


def get_alignment_milestones(path):
    LEAVES_TO_MILESTONES = {}
    ALIGNMENTS = []

    with open(path) as f:
        reader = csv.reader(f)
        # discard header row
        next(reader)
        for pos, row in enumerate(reader):
            milestone_id = row[0]
            greek_content = row[2]
            # @@@ Can't use the citation field as-is due to discrepancies
            # in the source material
            # citation = row[1]
            citation = get_citation(greek_content)
            # @@@ `map_leaves_to_milestones` could return text extracted from leaves
            # in a generator, but since the greek_content contains partial references.
            # we end up needing to just extract it from the CSV data
            cleaned_greek_content = transform_greek_content(greek_content)

            # Map leaves to milestones
            map_leaves_to_milestones(
                LEAVES_TO_MILESTONES, milestone_id, pos, cleaned_greek_content
            )

            ALIGNMENTS.append(
                {
                    "id": milestone_id,
                    "citation": citation,
                    "greek_content": cleaned_greek_content,
                    "english_content": [
                        # @@@ continuation
                        (citation, row[3], LINE_KIND_UNKNOWN)
                    ],
                }
            )

    for milestone_idx, alignment in enumerate(ALIGNMENTS):
        for pos, entry in enumerate(alignment["greek_content"]):
            offsets = LEAVES_TO_MILESTONES[entry[0]]
            if [milestone_idx] == offsets:
                alignment["greek_content"][pos] += (LINE_KIND_NEW,)
            elif offsets[0] == milestone_idx:
                alignment["greek_content"][pos] += (LINE_KIND_CONTINUES,)
            else:
                alignment["greek_content"][pos] += (LINE_KIND_CONTINUATION,)

    return {"ALIGNMENTS": ALIGNMENTS, "LEAVES_TO_MILESTONES": LEAVES_TO_MILESTONES}


def _alignment_chunk_obj(version, line_lookup, alignment, milestone, milestone_idx):
    chunk_obj = TextAlignmentChunk(
        citation=milestone["citation"],
        idx=milestone_idx,
        version=version,
        alignment=alignment,
        items=[milestone["greek_content"], milestone["english_content"]],
    )
    try:
        start_ref, end_ref = milestone["citation"].split("-")
    except ValueError:
        start_ref = end_ref = milestone["citation"]
    start_chapter, start_verse = [int(i) for i in start_ref.split(".")]
    end_chapter, end_verse = [int(i) for i in end_ref.split(".")]

    try:
        chunk_obj.start = line_lookup[f"{start_chapter}.{start_verse}"]
        chunk_obj.end = line_lookup[f"{end_chapter}.{end_verse}"]
        return chunk_obj
    except KeyError:
        # greek version mismatch; could be others
        print(
            f"Skipping milestone due to line(s) not found.  [alignment.name={alignment.name} citation={milestone['citation']} milestone_id={milestone['id']}]"
        )
        return


def _build_line_lookup(version):
    lookup = {}
    citation_scheme = version.metadata["citation_scheme"]
    for line in version.get_descendants().filter(kind=citation_scheme[-1]):
        lookup[line.ref] = line
    return lookup


def _import_alignment(data):
    full_content_path = os.path.join(ALIGNMENTS_DATA_PATH, data["content_path"])

    milestones = get_alignment_milestones(full_content_path)
    # the version urns in data need a trailing colon
    version_urn = f'{data["version_urn"]}:'
    version = Node.objects.get(urn=version_urn)
    alignment, _ = TextAlignment.objects.update_or_create(
        version=version,
        name=data["metadata"]["name"],
        defaults=dict(metadata=data["metadata"]),
    )

    chunks_created = 0
    line_lookup = _build_line_lookup(version)
    to_create = []
    for milestone_idx, milestone in enumerate(milestones["ALIGNMENTS"]):
        chunk = _alignment_chunk_obj(
            version, line_lookup, alignment, milestone, milestone_idx
        )
        if chunk:
            to_create.append(chunk)
            chunks_created += 1
    created = len(TextAlignmentChunk.objects.bulk_create(to_create, batch_size=500))
    assert created == chunks_created


@transaction.atomic(savepoint=False)
def import_alignments(reset=False):
    if reset:
        TextAlignment.objects.all().delete()

    alignments_metadata = json.load(open(ALIGNMENTS_METADATA_PATH))
    for alignment_data in alignments_metadata["alignments"]:
        _import_alignment(alignment_data)
