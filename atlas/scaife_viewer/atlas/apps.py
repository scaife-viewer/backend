from django.apps import AppConfig as BaseAppConfig
from django.conf import settings
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
    if connection.vendor == "sqlite" and connection.alias == settings.SV_ATLAS_DB_LABEL:
        cursor = connection.cursor()
        cursor.execute("PRAGMA synchronous=OFF;")
        cursor.execute("PRAGMA cache_size=100000;")
        cursor.execute("PRAGMA journal_mode=MEMORY;")
        # TODO: Add note to documentation and consider
        # alternatives to django-treebeard implementation
        # 😱 TIL:
        # https://code.djangoproject.com/ticket/9905
        # https://code.djangoproject.com/ticket/15659
        # https://docs.djangoproject.com/en/3.1/ref/databases/#substring-matching-and-case-sensitivity
        cursor.execute("PRAGMA case_sensitive_like=ON;")


connection_created.connect(tweak_sqlite_pragma)
