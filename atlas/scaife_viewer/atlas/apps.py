from django.apps import AppConfig as BaseAppConfig
from django.db.backends.signals import connection_created
from django.utils.translation import ugettext_lazy as _


class AppConfig(BaseAppConfig):

    name = "scaife_viewer.atlas"
    label = "scaife_viewer_atlas"
    verbose_name = _("Scaife Viewer ATLAS")


def tweak_sqlite_pragma(sender, connection, **kwargs):
    """
    Customize PRAGMA settings for SQLite
    """
    # TODO: Bind this only to the ATLAS database,
    # rather than assuming any SQLite connection
    if connection.vendor == "sqlite":
        cursor = connection.cursor()
        cursor.execute("PRAGMA synchronous=OFF;")
        cursor.execute("PRAGMA cache_size=100000;")
        cursor.execute("PRAGMA journal_mode=MEMORY;")


connection_created.connect(tweak_sqlite_pragma)
