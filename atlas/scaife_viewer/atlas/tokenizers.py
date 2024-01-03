import csv
import sys

from .models import Node, Token
from .utils import get_lowest_citable_nodes


LIMIT = None


def get_tokens_from_csv(version_exemplar_urn, path):
    # NOTE: Testing against Iliad, pandas.read_csv took nearly
    # twice as long; we may revisit it in the future
    # if we have more processing to perform

    version_exemplar = Node.objects.get(urn=version_exemplar_urn)
    text_part_to_id_map = {}
    text_parts = get_lowest_citable_nodes(version_exemplar)
    for ref, id in text_parts.values_list("ref", "id"):
        text_part_to_id_map[ref] = id

    tokens = []
    with path.open() as f:
        for row in csv.DictReader(f):
            text_part_ref = row["ve_ref"].split(".t", maxsplit=1)[0]
            space_after = row.pop("space_after", "")
            # NOTE: We mimic pandas.read_csv's default behavior:
            # "Values to consider as False in addition to case-insensitive variants of “False”."
            # refs https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html?highlight=read_csv#
            space_after = False if space_after.lower() == "false" else True
            tokens.append(
                dict(
                    text_part_id=text_part_to_id_map[text_part_ref],
                    space_after=space_after,
                    **row,
                )
            )
    return tokens


def tokenize_text_parts(version_exemplar_urn, force=True):
    if force:
        Token.objects.filter(text_part__urn__icontains=version_exemplar_urn).delete()

    version_exemplar = Node.objects.get(urn=version_exemplar_urn)
    text_parts = get_lowest_citable_nodes(version_exemplar)
    counters = {"token_idx": 0}
    to_create = []
    for text_part in text_parts:
        if not text_part.text_content:
            continue
        to_create.extend(Token.tokenize(text_part, counters))
    created = len(Token.objects.bulk_create(to_create, batch_size=LIMIT))
    print(f"Created {created} tokens for {version_exemplar}", file=sys.stderr)


def tokenize_all_text_parts_serial(reset=False):
    version_exemplar_nodes = Node.objects.filter(kind__in=["version", "exemplar"])
    for node in version_exemplar_nodes:
        tokenize_text_parts(node.urn, force=reset)


def tokenize_all_text_parts(reset=False):
    token_callable = tokenize_all_text_parts_serial
    # TODO: We may want to make pandas an explicit dependency of ATLAS
    try:
        print("Using parallel tokenizer via pandas.read_csv")
        from .parallel_tokenizers import (
            tokenize_all_text_parts_parallel as token_callable,
        )
    except ImportError:
        print("pandas not found; falling back to serial tokenizer")
    token_callable(reset=reset)
