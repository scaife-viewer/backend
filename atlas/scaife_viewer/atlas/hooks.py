import logging
from pathlib import Path
from typing import Iterable

from . import constants
from .resolvers.default import resolve_library
from .utils import get_paths_matching_predicate


logger = logging.getLogger(__name__)

ALLOWABLE_CTS_INGESTION_EXCEPTIONS = (KeyError, ValueError, TypeError, AttributeError)


def ensure_trailing_colon(urn):
    if not urn.endswith(":"):
        return f"{urn}:"
    return urn


def _get_annotation_paths(path, predicate=None) -> Iterable:
    """
    Returns paths or an empty list.
    """
    if not path.exists():
        return []
    return get_paths_matching_predicate(path, predicate=predicate)


class DefaultHookSet:
    # NOTE: Site developers can override attrs on their hookset class
    # to override the choices and default value for TextAnnotation.kind
    TEXT_ANNOTATION_DEFAULT_KIND = constants.TEXT_ANNOTATION_KIND_SCHOLIA
    TEXT_ANNOTATION_KIND_CHOICES = constants.TEXT_ANNOTATION_KIND_CHOICES

    def resolve_library(self):
        return resolve_library()

    def can_access_urn(self, request, urn):
        return True

    def get_human_lang(self, value):
        return constants.HUMAN_FRIENDLY_LANGUAGE_MAP.get(value, value)

    def get_importer_class(self):
        from .importers.versions import CTSImporter  # noqa: avoids circular import

        return CTSImporter

    def extract_cts_text_group_metadata(self, text_group):
        return dict(
            urn=f"{ensure_trailing_colon(text_group.urn)}",
            name=[dict(lang="eng", value=str(text_group.label))],
        )

    def extract_cts_work_metadata(self, work):
        # FIXME: backport `lang` attr to scaife-viewer-core
        lang = getattr(work, "lang", work.metadata.lang)
        return dict(
            urn=f"{ensure_trailing_colon(work.urn)}",
            lang=lang,
            title=[
                {
                    # TODO: provide a better api for work.label lang
                    "lang": work.label._language,
                    "value": str(work.label),
                }
            ],
        )

    def get_first_passage_urn(self, version):
        try:
            return str(version.first_passage().urn)
        except ALLOWABLE_CTS_INGESTION_EXCEPTIONS:
            msg = f'Could not extract first_passage_urn [urn="{version.urn}"]'
            logger.warning(msg)
            return None

    def extract_cts_version_metadata(self, version):
        first_passage_urn = self.get_first_passage_urn(version)

        # TODO: Move textpart level extractors out to another interface within `Library`
        try:
            textpart_metadata = self.extract_cts_textpart_metadata(version)
        except ALLOWABLE_CTS_INGESTION_EXCEPTIONS:
            msg = f'Could not extract textpart_metadata [urn="{version.urn}"]'
            logger.warning(msg)
            textpart_metadata = {}

        return dict(
            urn=f"{ensure_trailing_colon(version.urn)}",
            version_kind=version.kind,
            # TODO: Other ways to expose this on `Library`
            textpart_metadata=textpart_metadata,
            first_passage_urn=first_passage_urn,
            citation_scheme=[c.name for c in version.metadata.citation],
            label=[
                {
                    # TODO: provide a better api for version.label lang
                    "lang": version.label._language,
                    "value": str(version.label),
                }
            ],
            description=[
                {
                    # TODO: provide a better api for version.description lang
                    "lang": version.description._language,
                    "value": str(version.description),
                }
            ],
            lang=version.lang,
        )

    def should_ingest_lowest_citable_nodes(self, cts_version_obj):
        return True

    def extract_cts_textpart_metadata(self, version):
        version_urn = ensure_trailing_colon(version.urn)
        # TODO: define this on cts.Text?
        metadata = {}
        toc = version.toc()
        for ref_node in toc.num_resolver.glob(toc.root, "*"):
            textpart_urn = f"{version_urn}{ref_node}"
            metadata[textpart_urn] = {
                "first_passage_urn": next(toc.chunks(ref_node), None).urn,
            }

            if self.should_ingest_lowest_citable_nodes(version):
                for child in ref_node.descendants:
                    child_urn = f"{version_urn}{child}"
                    metadata[child_urn] = None
        return metadata

    def run_ingestion_pipeline(self, outf):
        from .ingestion_pipeline import run_ingestion_pipeline

        return run_ingestion_pipeline(outf)

    def get_token_annotation_paths(self):
        from .conf import settings  # noqa; avoids race condition

        path = Path(
            settings.SV_ATLAS_DATA_DIR,
            "annotations",
            "token-annotations",
        )

        def isdir(path):
            return path.is_dir()

        return _get_annotation_paths(path, predicate=isdir)

    def get_text_annotation_paths(self):
        from .conf import settings  # noqa; avoids race condition

        path = Path(
            settings.SV_ATLAS_DATA_DIR,
            "annotations",
            "text-annotations",
        )
        return _get_annotation_paths(path)

    def get_syntax_tree_annotation_paths(self):
        from .conf import settings  # noqa; avoids race condition

        path = Path(settings.SV_ATLAS_DATA_DIR, "annotations", "syntax-trees")
        return _get_annotation_paths(path)

    def get_metadata_collection_annotation_paths(self):
        from .conf import settings  # noqa; avoids race condition

        path = Path(settings.SV_ATLAS_DATA_DIR, "annotations", "metadata-collections")
        return _get_annotation_paths(path)

    def get_dictionary_annotation_paths(self):
        from .conf import settings  # noqa; avoids race condition

        path = Path(settings.SV_ATLAS_DATA_DIR, "annotations", "dictionaries")
        # FIXME: Standardize "default" annotation formats; currently we have a mixture
        # of manifest or "all-in-one" files that makes things inconsistent
        predicate = lambda x: x.suffix == ".json" or x.is_dir()  # noqa
        return _get_annotation_paths(path, predicate=predicate)

    def get_prepared_tokens(self, version_urn):
        from .parallel_tokenizers import prepare_tokens

        return prepare_tokens(version_urn)


class HookProxy:
    def __getattr__(self, attr):
        from .conf import settings  # noqa; avoids race condition

        return getattr(settings.SV_ATLAS_HOOKSET, attr)


hookset = HookProxy()
