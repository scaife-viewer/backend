import concurrent.futures
import sys

from .conf import settings
from .models import Node, Token
from .utils import get_lowest_citable_nodes


LIMIT = 500


def tokenize_text_parts(version_exemplar_urn, force=True):
    if force:
        Token.objects.filter(text_part__urn__icontains=version_exemplar_urn).delete()

    version_exemplar = Node.objects.get(urn=version_exemplar_urn)
    text_parts = get_lowest_citable_nodes(version_exemplar)
    counters = {"token_idx": 0}
    to_create = []
    for text_part in text_parts:
        to_create.extend(Token.tokenize(text_part, counters))
    created = len(Token.objects.bulk_create(to_create, batch_size=LIMIT))
    print(f"Created {created} tokens for {version_exemplar}", file=sys.stderr)


def tokenize_all_text_parts_parallel(reset=False):
    exceptions = False
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=settings.SV_ATLAS_INGESTION_CONCURRENCY
    ) as executor:
        version_exemplar_nodes = Node.objects.filter(kind__in=["version", "exemplar"])
        urn_futures = {
            executor.submit(tokenize_text_parts, node.urn, force=reset): node.urn
            for node in version_exemplar_nodes
        }
        for f in concurrent.futures.as_completed(urn_futures):
            urn = urn_futures[f]
            try:
                f.result()
            except Exception as exc:
                exceptions = True
                print("{} generated an exception: {}".format(urn, exc))
    if exceptions:
        raise AssertionError("Exceptions were encountered tokenizing textparts")


def tokenize_all_text_parts_serial(reset=False):
    version_exemplar_nodes = Node.objects.filter(kind__in=["version", "exemplar"])
    for node in version_exemplar_nodes:
        tokenize_text_parts(node.urn, force=reset)


def tokenize_all_text_parts(reset=False):
    # FIXME: Improve reliability of parallel tokenizer
    return tokenize_all_text_parts_serial(reset=reset)
