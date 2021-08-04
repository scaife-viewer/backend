import concurrent.futures
import csv
import sqlite3
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

# FIXME: Currently required due to how macOS spawns ProcessPool workers
import django; django.setup();

from django import db
from django.conf import settings
from django.utils.text import slugify

import pandas

from scaife_viewer.atlas.models import Node, Token

from .utils import get_lowest_citable_nodes


# TODO: Prefer logger


def prepare_tokens(version_exemplar_urn):
    # TODO: Consider supporting the `reset` kwarg
    print("Querying...")
    version_exemplar = Node.objects.get(urn=version_exemplar_urn)
    text_parts = get_lowest_citable_nodes(version_exemplar)
    counters = {"token_idx": 0}
    to_create = []
    print("Tokenizing...")
    # TODO: Prefer a context manager for timing
    start = time.time()
    for text_part in text_parts:
        to_create.extend(Token.tokenize(text_part, counters, as_dict=True))
    end = time.time()
    print(f"Tokenized {len(to_create)} tokens in {end - start} seconds")
    return to_create


def write_to_csv(dirpath, urn, token_instances, fields=None):
    if fields is None:
        fields = token_instances[0].keys()

    print("Preparing CSV...")
    start = time.time()
    path = Path(dirpath, f"{slugify(urn)}.csv")
    # TODO: Consider refactoring via SpooledTemporaryFile
    with open(path, "w") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for token in token_instances:
            writer.writerow(token)
    end = time.time()
    print(f"Prepared [elapsed={end-start}]")
    return path


def insert_from_csv(path):
    print("Inserting...")
    start = time.time()
    table_name = "scaife_viewer_atlas_token"
    conn = sqlite3.connect(settings.DATABASES["default"]["NAME"])
    pandas.read_csv(path).to_sql(table_name, conn, if_exists="append", index=False)
    end = time.time()
    print(f"Inserted tokens [elapsed={end-start}]", file=sys.stderr)


def tokenize_text_parts(dirpath, node_urn, force=False):
    tokens = prepare_tokens(node_urn)
    # TODO: We may also rewrite this to append to a file or throw onto
    # another processing queue
    path = write_to_csv(dirpath, node_urn, tokens)
    return path


def process_csvs(paths):
    for path in paths:
        insert_from_csv(path)


def tokenize_all_text_parts_parallel(reset=False):
    if reset:
        Token.objects.all()._raw_delete("default")

    exceptions = []
    start = time.time()
    paths_to_ingest = []
    # TODO: Make tempdir configurable
    tempdir = TemporaryDirectory()
    dirpath = Path(tempdir.name)
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=settings.SV_ATLAS_INGESTION_CONCURRENCY
    ) as executor:
        node_urns = list(
            Node.objects.filter(kind__in=["version", "exemplar"]).values_list(
                "urn", flat=True
            )
        )
        # NOTE: avoids locking protocol errors from SQLite
        db.connections.close_all()
        urn_futures = {
            executor.submit(tokenize_text_parts, dirpath, urn, force=reset): urn
            for urn in node_urns
        }
        for f in concurrent.futures.as_completed(urn_futures):
            urn = urn_futures[f]
            try:
                paths_to_ingest.append(f.result())
            except Exception as exc:
                exceptions.append(exc)
                print("{} generated an exception: {}".format(urn, exc))
    if exceptions:
        raise exceptions[0]

    process_csvs(paths_to_ingest)
    end = time.time()
    print(f"Elapsed: {end-start}")
    # TODO: call `cleanup` on failure too
    tempdir.cleanup()
