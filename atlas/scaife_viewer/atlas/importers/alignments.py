import csv
import json
import os
import re

from django.conf import settings
from django.utils.text import slugify

from ..models import (
    Node,
    TextAlignment,
    TextAlignmentRecord,
    TextAlignmentRecordRelation,
    Token,
)


ALIGNMENTS_DATA_PATH = os.path.join(settings.PROJECT_ROOT, "data", "alignments")
ALIGNMENTS_METADATA_PATH = os.path.join(ALIGNMENTS_DATA_PATH, "metadata.json")

# LINE_KIND_UNKNOWN = None
# LINE_KIND_NEW = "new"
# LINE_KIND_CONTINUES = "continues"
# LINE_KIND_CONTINUATION = "continuation"

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
                        # (citation, row[3], LINE_KIND_UNKNOWN)
                        (citation, row[3])
                    ],
                }
            )

    # @@@ restore continuation data
    # for milestone_idx, alignment in enumerate(ALIGNMENTS):
    #     for pos, entry in enumerate(alignment["greek_content"]):
    #         offsets = LEAVES_TO_MILESTONES[entry[0]]
    #         if [milestone_idx] == offsets:
    #             alignment["greek_content"][pos] += (LINE_KIND_NEW,)
    #         elif offsets[0] == milestone_idx:
    #             alignment["greek_content"][pos] += (LINE_KIND_CONTINUES,)
    #         else:
    #             alignment["greek_content"][pos] += (LINE_KIND_CONTINUATION,)

    return {"ALIGNMENTS": ALIGNMENTS, "LEAVES_TO_MILESTONES": LEAVES_TO_MILESTONES}


def _alignment_record_obj(version, line_lookup, alignment, milestone, milestone_idx):
    chunk_obj = TextAlignmentRecord(
        citation=milestone["citation"],
        idx=milestone_idx,
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


def _build_token_lookup(version):
    lookup = {}
    for token in Token.objects.filter(
        text_part__urn__startswith=version.urn
    ).select_related("text_part"):
        # @@@ ve_ref
        ve_ref = f"{token.text_part.ref}.{token.position}"
        lookup[ve_ref] = token
    return lookup


def _import_alignment(data):
    full_content_path = os.path.join(ALIGNMENTS_DATA_PATH, data["content_path"])

    milestones = get_alignment_milestones(full_content_path)
    versions = Node.objects.filter(urn__in=data["version_urns"])
    alignment, _ = TextAlignment.objects.update_or_create(
        name=data["metadata"]["name"],
        slug=slugify(data["metadata"]["name"]),
        defaults=dict(metadata=data["metadata"]),
    )
    alignment.versions.set(versions)

    version = versions.get(urn=data["version_urns"][0])
    chunks_created = 0
    line_lookup = _build_line_lookup(version)
    to_create = []
    for milestone_idx, milestone in enumerate(milestones["ALIGNMENTS"]):
        chunk = _alignment_record_obj(
            version, line_lookup, alignment, milestone, milestone_idx
        )
        if chunk:
            to_create.append(chunk)
            chunks_created += 1
    created = len(TextAlignmentRecord.objects.bulk_create(to_create, batch_size=500))
    assert created == chunks_created

    # @@@ stop-gap to maintain parity, dreadfully slow
    # @@@ can we bulk set many to many ?
    token_lookup = _build_token_lookup(version)
    for chunk in alignment.records.all():
        ref = chunk.citation.split("-")[0]
        first_token = token_lookup[f"{ref}.1"]
        relation = TextAlignmentRecordRelation.objects.create(
            version=version, alignment_record=chunk, citation=chunk.citation,
        )
        relation.tokens.set([first_token])


def import_alignments(reset=False):
    if reset:
        TextAlignment.objects.all().delete()

    alignments_metadata = json.load(open(ALIGNMENTS_METADATA_PATH))
    for alignment_data in alignments_metadata["alignments"]:
        _import_alignment(alignment_data)


def sentence_alignment_fresh_start():
    version_a = Node.objects.get(urn="urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:")
    version_b = Node.objects.get(urn="urn:cts:greekLit:tlg0012.tlg001.perseus-eng3:")
    alignment = TextAlignment(
        name="Iliad Sentence Alignment", slug="iliad-sentence-alignment"
    )
    alignment.save()
    alignment.versions.set([version_a, version_b])

    record = TextAlignmentRecord(citation="1.1-1.7", alignment=alignment, idx=0)
    record.save()

    relation_a = TextAlignmentRecordRelation(
        version=version_a, record=record, citation="1.1-1.7"
    )
    relation_a.save()
    text_parts = version_a.get_descendants().filter(kind="line")[0:7]
    relation_a.tokens.set(Token.objects.filter(text_part__in=text_parts))

    relation_b = TextAlignmentRecordRelation(
        # @@@ citation is backwards incompatible with prior data
        version=version_b,
        record=record,
        citation="1.1",
    )
    relation_b.save()
    text_parts = version_b.get_descendants().filter(kind="card")[0:1]
    relation_b.tokens.set(Token.objects.filter(text_part__in=text_parts)[0:63])

    record.items = list(record.denorm_relations())
    record.save()

    alignment = TextAlignment.objects.first()
    record = TextAlignmentRecord(citation="1.9-1.12", alignment=alignment, idx=3)
    record.save()

    relation_a = TextAlignmentRecordRelation(
        version=version_a, record=record, citation="1.9-1.12"
    )
    relation_a.save()
    text_parts = list(version_a.get_descendants().filter(kind="line")[8:12])
    tokens = []
    tokens += text_parts[0].tokens.filter(position__gte=5)
    for text_part in text_parts[1:-1]:
        tokens.extend(text_part.tokens.all())
    tokens += text_parts[-1].tokens.filter(position=1)
    relation_a.tokens.set(tokens)

    relation_b = TextAlignmentRecordRelation(
        version=version_b, record=record, citation="1.1"
    )
    relation_b.save()
    text_parts = version_b.get_descendants().filter(kind="card")[0:1]
    relation_b.tokens.set(Token.objects.filter(text_part__in=text_parts)[83:115])

    record.items = list(record.denorm_relations())
    record.save()

    version_a = Node.objects.get(urn="urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:")
    version_b = Node.objects.get(urn="urn:cts:greekLit:tlg0012.tlg001.perseus-eng3:")
    alignment = TextAlignment(name="Iliad Word Alignment", slug="iliad-word-alignment")
    alignment.save()
    alignment.versions.set([version_a, version_b])

    record = TextAlignmentRecord(citation="1.1.2", alignment=alignment, idx=1)
    record.save()

    relation_a = TextAlignmentRecordRelation(
        version=version_a, record=record, citation="1.1.2"
    )
    relation_a.save()
    tokens = Token.objects.filter(
        text_part__urn="urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1", position=2
    )
    relation_a.tokens.set(tokens)

    relation_b = TextAlignmentRecordRelation(
        # @@@ citation is backwards incompatible with prior data
        version=version_b,
        record=record,
        citation="1.1.3",
    )
    relation_b.save()
    tokens = Token.objects.filter(
        text_part__urn="urn:cts:greekLit:tlg0012.tlg001.perseus-eng3:1.1", position=3
    )
    relation_b.tokens.set(tokens)


def process_cex(path):
    # TODO: Better processing of the entire CEX file / CITE model is desired
    lookup = {}
    with open(path) as f:
        for line in f:
            if line.startswith("urn:cite2:ducat:alignments.temp:") and line.count(
                "urn:cite2:cite:verbs.v1:aligns"
            ):
                record_urn, _, citation_urn = line.strip().split("#")
                lang = "greek" if citation_urn.count("grc") else "english"
                alignment = lookup.setdefault(record_urn, {"greek": [], "english": []})
                alignment[lang].append(citation_urn)

    def sort_textpart(urn):
        _, ref = urn.rsplit(":", maxsplit=1)
        book, line, position = [int(i) for i in ref.split(".")]
        return (book, line, position)

    unique_alignments = set()
    for record_urn, alignment in lookup.items():
        greek = sorted(alignment["greek"], key=sort_textpart)
        english = sorted(alignment["english"], key=sort_textpart)
        sort_key = sort_textpart(alignment["greek"][0])
        unique_alignments.add((sort_key, record_urn, tuple(greek), tuple(english)))

    unique_alignments = list(unique_alignments)
    alignments = sorted(unique_alignments, key=lambda x: x[0])

    version_a = Node.objects.get(urn="urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:")
    version_b = Node.objects.get(urn="urn:cts:greekLit:tlg0012.tlg001.perseus-eng3:")
    slug_fragment = os.path.basename(path).rsplit(".")[-2].split("_")[0]
    alignment = TextAlignment(
        label=f"Iliad {slug_fragment.title()} Alignment",
        urn=f"urn:cite2:scaife-viewer:alignment:tlg0012.tlg001.perseus-grc2-{slug_fragment}-alignment",
    )
    alignment.save()
    alignment.versions.set([version_a, version_b])

    def get_ref(urn):
        _, ref = urn.rsplit(":", maxsplit=1)
        return ref

    def get_textpart_ref(urn):
        ref = get_ref(urn)
        text_part_ref, position = ref.rsplit(".", maxsplit=1)
        return text_part_ref

    idx = 0
    # TODO: review how we might make use of sort key from CEX
    # TODO: sorting versions from Ducat too, especially since Ducat doesn't have 'em
    # maybe something for CITE tools?
    for _, record_urn, greek, english in alignments:
        record = TextAlignmentRecord(idx=idx, alignment=alignment, urn=record_urn)
        record.save()
        idx += 1

        relation_a = TextAlignmentRecordRelation(version=version_a, record=record,)
        relation_a.save()
        tokens = []
        # TODO: Can we build up a veref map and validate?
        for urn in greek:
            ref = get_ref(urn)
            text_part_ref, position = ref.rsplit(".", maxsplit=1)
            text_part_urn = f"{version_a.urn}{text_part_ref}"
            tokens.append(
                Token.objects.get(text_part__urn=text_part_urn, position=position)
            )
        relation_a.tokens.set(tokens)

        relation_b = TextAlignmentRecordRelation(version=version_b, record=record,)
        relation_b.save()

        # TODO: veref map as above
        tokens = []
        for urn in english:
            ref = get_ref(urn)
            text_part_ref, position = ref.rsplit(".", maxsplit=1)
            text_part_urn = f"{version_b.urn}{text_part_ref}"
            tokens.append(
                Token.objects.get(text_part__urn=text_part_urn, position=position)
            )
        relation_b.tokens.set(tokens)
        # TODO: review query counts here and some of our SQL hacks
