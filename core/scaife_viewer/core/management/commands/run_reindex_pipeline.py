from io import StringIO
import logging

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):

    help = "Run re-indexing pipeline"

    def handle(self, *args, **options):
        # TODO: Update content
        # TODO: Load content locally (drop scaife-cts-api)
        # TODO: Re-use local content (tarball + ATLAS db + cache file)
        # Create a new index
        with StringIO() as f:
            call_command("create_index", stdout=f)
            index_name = f.getvalue().strip()
        self.stdout.write(index_name)
        # Pass that index name to the indexer command via `call_command`
        # TODO: Set up lemmatization pipeline
        # TODO: Set up "diff" or "filter based on repo" functionality
        call_command("indexer", **dict(
            index_name=index_name,
            limit=100
        ))
        # If unsuccesful, raise error
        # Else write index name to env var or a config file
        # Index name (and possibly other tarball / data bits)
        # can be passed to a promotion script
        # TODO: Remove Varnish / Fastly in favor of app-level caching

