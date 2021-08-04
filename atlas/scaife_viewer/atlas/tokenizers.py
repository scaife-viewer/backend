import sys

from .models import Node, Token
from .utils import get_lowest_citable_nodes


LIMIT = None


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
        print("Loading parallel tokenizer")
        from .parallel_tokenizers import (
            tokenize_all_text_parts_parallel as token_callable,
        )
    except ImportError:
        print("pandas not found; falling back to serial tokenizer")
    token_callable(reset=reset)
