import concurrent.futures
import csv
import logging
import sqlite3
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import django

import pandas
import tqdm


# NOTE: django.setup() is invoked due to how macOS spawns the ProcessPool workers;
# as a result, the usual django imports are done slightly differently in this file.
django.setup()


logger = logging.getLogger(__name__)


def _get_lowest_citable_nodes(urn):
    # NOTE: This is done to wrap get_lowest_citable_nodes;
    # due to the use of django.setup() above, this would otherwise cause a
    # circular import error.
    from .utils import get_lowest_citable_nodes  # noqa:

    return get_lowest_citable_nodes(urn)


def prepare_tokens(version_exemplar_urn):
    Token = django.apps.apps.get_model("scaife_viewer_atlas.Token")
    Node = django.apps.apps.get_model("scaife_viewer_atlas.Node")

    # TODO: Consider supporting the `reset` kwarg
    logger.info("Querying...")
    version_exemplar = Node.objects.get(urn=version_exemplar_urn)
    text_parts = _get_lowest_citable_nodes(version_exemplar)
    counters = {"token_idx": 0}
    to_create = []
    logger.info("Tokenizing...")
    # TODO: Prefer a context manager for timing
    start = time.time()
    for text_part in text_parts:
        to_create.extend(Token.tokenize(text_part, counters, as_dict=True))
    end = time.time()
    logger.info(f"Tokenized {len(to_create)} tokens in {end - start} seconds")
    return to_create


def write_to_csv(dirpath, urn, token_instances, fields=None):
    # NOTE: Boolean fields (such as `space_after`) are encoded in the
    # CSV as strings, e.g. "True" and "False".
    # pandas read_csv will convert True and False by default.
    if fields is None:
        fields = token_instances[0].keys()

    logger.info("Preparing CSV...")
    start = time.time()
    path = Path(dirpath, f"{django.utils.text.slugify(urn)}.csv")
    # TODO: Consider refactoring via SpooledTemporaryFile
    with open(path, "w") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for token in token_instances:
            writer.writerow(token)
    end = time.time()
    logger.info(f"Prepared [elapsed={end-start}]")
    return path


def insert_from_csv(path):
    logger.info("Inserting...")
    start = time.time()
    table_name = "scaife_viewer_atlas_token"
    sv_atlas_db_name = django.conf.settings.DATABASES[
        django.conf.settings.SV_ATLAS_DB_LABEL
    ]["NAME"]
    conn = sqlite3.connect(sv_atlas_db_name)
    pandas.read_csv(path, keep_default_na=False).to_sql(
        table_name, conn, if_exists="append", index=False
    )
    end = time.time()
    logger.info(f"Inserted tokens [elapsed={end-start}]", file=sys.stderr)


def tokenize_text_parts(dirpath, node_urn):
    from .hooks import hookset

    tokens = hookset.get_prepared_tokens(node_urn)
    if tokens:
        # TODO: We may also rewrite this to append to a file or throw onto
        # another processing queue
        return write_to_csv(dirpath, node_urn, tokens)


def process_csvs(paths):
    for path in tqdm.tqdm(paths):
        insert_from_csv(path)


def tokenize_textparts_and_insert(dirpath, node_urn, reset=False):
    """
    Read text parts from the database, generate token CSV and insert
    tokens

    Usage:

    ```python
    from pathlib import Path

    from scaife_viewer.atlas.parallel_tokenizers tokenize_textparts_and_insert

    outdir = Path(".")
    version_urn = "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:"
    tokenize_textparts_and_insert(outdir, version_urn, reset=True)
    ```
    """
    Token = django.apps.apps.get_model("scaife_viewer_atlas.Token")
    tokenized_path = tokenize_text_parts(dirpath, node_urn)

    if not tokenized_path:
        return

    if reset:
        Token.objects.filter(text_part__urn__startswith=node_urn).delete()
    insert_from_csv(tokenized_path)


def tokenize_text_parts_parallel(node_urns):
    exceptions = []
    start = time.time()
    paths_to_ingest = []
    # TODO: Make tempdir configurable
    tempdir = TemporaryDirectory()
    dirpath = Path(tempdir.name)
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=django.conf.settings.SV_ATLAS_INGESTION_CONCURRENCY
    ) as executor:
        # NOTE: avoids locking protocol errors from SQLite
        django.db.connections.close_all()
        urn_futures = {
            executor.submit(tokenize_text_parts, dirpath, urn): urn for urn in node_urns
        }
        for f in tqdm.tqdm(
            concurrent.futures.as_completed(urn_futures), total=len(node_urns)
        ):
            urn = urn_futures[f]
            try:
                path = f.result()
                if path:
                    paths_to_ingest.append(path)
            except Exception as exc:
                exceptions.append(exc)
                logger.info("{} generated an exception: {}".format(urn, exc))
    if exceptions:
        raise exceptions[0]

    process_csvs(paths_to_ingest)
    end = time.time()
    duration = "{:.2f}".format(end - start)
    logger.info(f"Elapsed: {duration}")
    # TODO: call `cleanup` on failure too
    tempdir.cleanup()


def tokenize_all_text_parts_parallel(node_urns=None, reset=False):
    from django.conf import settings

    Token = django.apps.apps.get_model("scaife_viewer_atlas.Token")
    Node = django.apps.apps.get_model("scaife_viewer_atlas.Node")

    if reset:
        # NOTE: Using must specify the ATLAS db alias
        Token.objects.all()._raw_delete(using=settings.SV_ATLAS_DB_LABEL)
    if node_urns is None:
        node_urns = list(
            Node.objects.filter(kind__in=["version", "exemplar"]).values_list(
                "urn", flat=True
            )
        )
    return tokenize_text_parts_parallel(node_urns)
