import logging

from . import constants
from .resolvers.default import resolve_library


logger = logging.getLogger(__name__)


def ensure_trailing_colon(urn):
    if not urn.endswith(":"):
        return f"{urn}:"
    return urn


class DefaultHookSet:
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

    def extract_cts_version_metadata(self, version):
        urn = str(version.urn)

        try:
            first_passage_urn = str(version.first_passage().urn)
        except KeyError:
            msg = f'Could not extract first_passage_urn [urn="{urn}"]'
            logger.warning(msg)
            first_passage_urn = None

        # TODO: Move textpart level extractors out to another interface within `Library`
        try:
            textpart_metadata = self.extract_cts_textpart_metadata(version)
        except KeyError:
            msg = f'Could not extract textpart_metadata [urn="{urn}"]'
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

    def extract_cts_textpart_metadata(self, version):
        version_urn = ensure_trailing_colon(version.urn)
        # TODO: define this on cts.Text?
        metadata = {}
        toc = version.toc()
        for ref_node in toc.num_resolver.glob(toc.root, "*"):
            ref = ref_node.num
            textpart_urn = f"{version_urn}{ref}"
            metadata[textpart_urn] = {
                "first_passage_urn": next(toc.chunks(ref_node), None).urn,
            }
        return metadata

    def version_node_class(self):
        from .schema import VersionNode
        return VersionNode


class HookProxy:
    def __getattr__(self, attr):
        from .conf import settings  # noqa; avoids race condition

        return getattr(settings.SV_ATLAS_HOOKSET, attr)


hookset = HookProxy()
