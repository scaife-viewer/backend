import time
from decimal import Decimal

from django.core.management.base import BaseCommand

from ...cloud import CloudJob
from ...conf import settings
from ...indexer import DirectPusher, Indexer, PubSubPusher


class IndexerCommand(BaseCommand):

    help = "Indexes passages in Elasticsearch"

    def add_arguments(self, parser):
        parser.add_argument("--max-workers", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true", default=False)
        parser.add_argument("--urn-prefix")
        parser.add_argument("--chunk-size", type=int, default=100)
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--delete-index", action="store_true", default=False)
        parser.add_argument("--pusher", type=str, default="direct")
        parser.add_argument("--pubsub-project")
        parser.add_argument("--pubsub-topic")
        parser.add_argument("--morphology-path", type=str, default="")
        parser.add_argument("--index-name", type=str, default=None)

    def handle(self, *args, **options):
        # executor = concurrent.futures.ProcessPoolExecutor(max_workers=options["max_workers"])
        if options["pusher"] == "direct":
            pusher = DirectPusher(
                index_name=options.get("index_name"),
                chunk_size=options.get("chunk_size"),
            )
        elif options["pusher"] == "pubsub":
            pusher = PubSubPusher(options["pubsub_project"], options["pubsub_topic"])
        indexer = Indexer(
            pusher,
            options["morphology_path"],
            urn_prefix=options["urn_prefix"],
            chunk_size=options["chunk_size"],
            limit=options["limit"],
            dry_run=options["dry_run"],
            max_workers=options["max_workers"],
        )
        with Timer() as timer:
            indexer.index()
        elapsed = timer.elapsed.quantize(Decimal("0.00"))
        print(f"Finished in {elapsed}s")


if settings.SCAIFE_VIEWER_CORE_USE_CLOUD_INDEXER:
    # NOTE: Adds additional GCE metadata hooks
    # onto the indexing command
    class Command(CloudJob, IndexerCommand):
        pass

else:

    class Command(IndexerCommand):
        pass


class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, typ, value, traceback):
        self.elapsed = Decimal.from_float(time.perf_counter() - self.start)
