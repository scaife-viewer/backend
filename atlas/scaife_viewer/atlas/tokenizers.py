import sys

from .models import Node, Token


LIMIT = 500


def tokenize_text_parts(version_exemplar_urn, force=True):
    if force:
        Token.objects.filter(text_part__urn__icontains=version_exemplar_urn).delete()

    version_exemplar = Node.objects.get(urn=version_exemplar_urn)
    lowest_kind = version_exemplar.metadata["citation_scheme"][-1]
    text_parts = version_exemplar.get_descendants().filter(kind=lowest_kind)
    counters = {"token_idx": 0}
    to_create = []
    for text_part in text_parts:
        to_create.extend(Token.tokenize(text_part, counters))
    created = len(Token.objects.bulk_create(to_create, batch_size=LIMIT))
    print(f"Created {created} tokens for {version_exemplar}", file=sys.stderr)


def tokenize_all_text_parts(reset=False):
    for version_exemplar_node in Node.objects.filter(kind__in=["version", "exemplar"]):
        tokenize_text_parts(version_exemplar_node.urn, force=reset)
