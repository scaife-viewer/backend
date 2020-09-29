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
    # Data model
    DATA_DIR = None
    DATA_MODEL_ID = base64.b64encode(b"2020-09-08-001\n").decode()
    INGESTION_CONCURRENCY = None
    NODE_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    # GraphQL settings
    IN_MEMORY_PASSAGE_CHUNK_MAX = 2500

    # Database settings
    DB_LABEL = "atlas"
    DB_PATH = None

    # Other
    HOOKSET = "scaife_viewer.atlas.hooks.DefaultHookSet"

    class Meta:
        prefix = "sv_atlas"

    def configure_hookset(self, value):
        return load_path_attr(value)()

    def configure_data_dir(self, value):
        # NOTE: We've chosen an explicit `configure` method
        # vs making `DATA_DIR` a required field so we can check
        # that DATA_DIR is a non-None value.
        if value is None:
            msg = f"{self._meta.prefixed_name('DATA_DIR')} must be defined"
            raise ImproperlyConfigured(msg)
