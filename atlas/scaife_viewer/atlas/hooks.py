from . import constants


class DefaultHookSet:
    def resolve_library(self):
        # TODO: Document included resolvers
        # from .resolvers.cts import resolve_cts_collection_library as resolver_func
        from .resolvers.default import resolve_library as resolver_func

        return resolver_func()

    def can_access_urn(self, request, urn):
        return True

    def get_human_lang(self, value):
        return constants.HUMAN_FRIENDLY_LANGUAGE_MAP.get(value, value)


class HookProxy:
    def __getattr__(self, attr):
        from .conf import settings  # noqa; avoids race condition

        return getattr(settings.SV_ATLAS_HOOKSET, attr)


hookset = HookProxy()
