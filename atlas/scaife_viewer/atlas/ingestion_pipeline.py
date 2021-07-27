import importlib

from django.core.exceptions import ImproperlyConfigured


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


def run_ingestion_pipeline(outf):
    from .conf import settings  # noqa; avoids race condition

    pipeline_func_paths = settings.SV_ATLAS_INGESTION_PIPELINE

    for path in pipeline_func_paths:
        func = load_path_attr(path)
        outf.write(f"--[{path}]--")
        func(reset=True)
