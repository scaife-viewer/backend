import base64
import importlib

from django.conf import settings  # noqa
from django.core.exceptions import ImproperlyConfigured

from appconf import AppConf


def load_path_attr(path):
    i = path.rfind(".")
    module, attr = path[:i], path[i + 1 :]
    try:
        mod = importlib.import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured("Error importing {0}: '{1}'".format(module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured(
            "Module '{0}' does not define a '{1}'".format(module, attr)
        )
    return attr


class ATLASAppConf(AppConf):
    # `INGESTION_CONCURRENCY` defaults to number of processors
    # as reported by multiprocessing.cpu_count()
    INGESTION_CONCURRENCY = None

    IN_MEMORY_PASSAGE_CHUNK_MAX = 2500
    NODE_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    # `DATA_MODEL_ID` should be incremented when BI schema changes are made
    # to ATLAS models.
    # Site developers can use the value of this setting to help inform
    # that ATLAS content must be re-ingested when schema changes occur
    DATA_MODEL_ID = base64.b64encode(b"2020-09-08-001\n").decode()
    DB_LABEL = "atlas"
    DB_PATH = None
    HOOKSET = "scaife_viewer.atlas.hooks.DefaultHookSet"

    # required settings
    # DATA_DIR

    class Meta:
        prefix = "sv_atlas"
        required = ["DATA_DIR"]

    def configure_hookset(self, value):
        return load_path_attr(value)()
