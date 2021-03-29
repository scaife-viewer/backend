import os
import shutil
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from scaife_viewer.atlas.conf import settings
from scaife_viewer.atlas.data_model import VERSION

from ...hooks import hookset


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
        parser.add_argument(
            "--keep-resolver-cache",
            action="store_true",
            help="Keeps CTS resolver cache in place",
        )

    def do_db_prep(self, database_path, *args, **options):
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

        if hasattr(settings, "CTS_RESOLVER_CACHE_LOCATION") and not options.get(
            "keep_resolver_cache"
        ):
            resolver_path = settings.CTS_RESOLVER_CACHE_LOCATION
            if os.path.exists(resolver_path):
                shutil.rmtree(resolver_path)
                self.stdout.write("--[Removed existing CTS resolver cache]--")

        self.stdout.write("--[Processing ATLAS ingestion pipeline]--")
        hookset.run_ingestion_pipeline(self.stdout)

    def handle(self, *args, **options):
        database_path = settings.SV_ATLAS_DB_PATH

        if database_path is None:
            msg = "The SV_ATLAS_DB_PATH setting is missing and is required for this management command to work."
            raise ImproperlyConfigured(msg)

        workfile = os.path.join(Path(database_path).parent, f"atlas-{VERSION}-workfile")
        if not options.get("force") and os.path.exists(workfile):
            # we assume that another instance of the command is already running
            raise CommandError(f"ATLAS workfile exists: {workfile}")

        # open / create the workfile
        open(workfile, "w")
        try:
            self.do_db_prep(database_path, *args, **options)
        except Exception as e:
            # if we encounter an exception, we should not keep
            # the ATLAS database around
            if os.path.exists(database_path):
                self.stderr.write(f"Removing {os.path.basename(database_path)}")
                os.unlink(database_path)
            raise e
        finally:
            if os.path.exists(workfile):
                os.unlink(workfile)
