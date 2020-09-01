from django.apps import AppConfig as BaseAppConfig
from django.db.backends.signals import connection_created
from django.utils.translation import ugettext_lazy as _


class AppConfig(BaseAppConfig):

    name = "scaife_viewer.atlas"
    label = "scaife_viewer_atlas"
    verbose_name = _("Scaife Viewer ATLAS")


def tweak_sqlite(sender, connection, **kwargs):
    """Enable integrity constraint with sqlite."""
    if connection.vendor == "sqlite":
        cursor = connection.cursor()
        cursor.execute("PRAGMA synchronous=OFF;")
        cursor.execute("PRAGMA cache_size=100000;")
        cursor.execute("PRAGMA journal_mode=MEMORY;")


connection_created.connect(tweak_sqlite)
