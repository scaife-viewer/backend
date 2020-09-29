import os
import shutil

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import BaseCommand

from scaife_viewer.atlas.conf import settings

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
        database_path = settings.SV_ATLAS_DB_PATH

        if database_path is None:
            msg = "The SV_ATLAS_DB_PATH setting is missing and is required for this management command to work."
            raise ImproperlyConfigured(msg)

        db_path_exists = os.path.exists(database_path)

        reset_data = options.get("force") or not db_path_exists
        if not reset_data:
            self.stdout.write(f"Found existing ATLAS data at {database_path}")
            return

        if db_path_exists:
            os.remove(database_path)
            self.stdout.write("--[Removed existing ATLAS database]--")
        else:
            db_dir = os.path.dirname(database_path)
            os.makedirs(db_dir, exist_ok=True)

        db_label = settings.SV_ATLAS_DB_LABEL
        self.stdout.write(f'--[Running database migrations on "{db_label}"]--')
        call_command("migrate", database=db_label)

        if hasattr(settings, "CTS_RESOLVER_CACHE_LOCATION"):
            resolver_path = settings.CTS_RESOLVER_CACHE_LOCATION
            if os.path.exists(resolver_path):
                shutil.rmtree(resolver_path)
                self.stdout.write("--[Removed existing CTS resolver cache]--")

        self.stdout.write("--[Populating ATLAS db]--")
        importers.versions.import_versions()
