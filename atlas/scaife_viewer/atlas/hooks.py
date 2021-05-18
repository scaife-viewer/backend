import logging

from . import constants
from .resolvers.default import resolve_library


logger = logging.getLogger(__name__)


def ensure_trailing_colon(urn):
    if not urn.endswith(":"):
        return f"{urn}:"
    return urn


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
        except (KeyError, ValueError, TypeError):
            msg = f'Could not extract first_passage_urn [urn="{version.urn}"]'
            logger.warning(msg)
            return None

    def extract_cts_version_metadata(self, version):
        first_passage_urn = self.get_first_passage_urn(version)

        # TODO: Move textpart level extractors out to another interface within `Library`
        try:
            textpart_metadata = self.extract_cts_textpart_metadata(version)
        except (KeyError, ValueError, TypeError):
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


class HookProxy:
    def __getattr__(self, attr):
        from .conf import settings  # noqa; avoids race condition

        return getattr(settings.SV_ATLAS_HOOKSET, attr)


hookset = HookProxy()
