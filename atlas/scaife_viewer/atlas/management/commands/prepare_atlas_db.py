# TODO: Revisit cts assumptions
import os
import shutil

from django.core.management import call_command
from django.core.management.base import BaseCommand

from scaife_viewer.atlas.conf import settings
from scaife_viewer.atlas.library.models import Node
from scaife_viewer.cts import text_inventory

from ... import importers


class Command(BaseCommand):
    """
    Prepares data used by ATLAS
    """

    help = "Prepares data used by ATLAS"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Forces the ATLAS management command to run",
        )

    def handle(self, *args, **options):
        database_path = settings.ATLAS_CONFIG["ATLAS_DB_PATH"]
        db_path_exists = os.path.exists(database_path)

        reset_data = options.get("force") or not db_path_exists
        if not reset_data:
            self.stdout.write(f"Found existing ATLAS data at {database_path}")
            return

        if db_path_exists:
            os.remove(database_path)
            self.stdout.write("--[Removed existing ATLAS database]--")

        self.stdout.write('--[Running database migrations on "atlas"]--')
        call_command("migrate", database="atlas")

        resolver_path = settings.CTS_RESOLVER_CACHE_LOCATION
        if os.path.exists(resolver_path):
            shutil.rmtree(resolver_path)
            self.stdout.write("--[Removed existing CTS resolver cache]--")

        self.stdout.write("--[Priming CTS Resolver cache]--")
        text_inventory()

        self.stdout.write("--[Populating ATLAS db]--")
        importers.versions.import_versions()
