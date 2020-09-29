from . import constants
from .resolvers.default import resolve_library


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
        return dict(
            urn=f"{ensure_trailing_colon(version.urn)}",
            version_kind=version.kind,
            # TODO: provide first_passage_urn
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


class HookProxy:
    def __getattr__(self, attr):
        from .conf import settings  # noqa; avoids race condition

        return getattr(settings.SV_ATLAS_HOOKSET, attr)


hookset = HookProxy()
