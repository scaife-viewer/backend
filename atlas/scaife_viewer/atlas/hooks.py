class DefaultHookSet:
    def resolve_library(self):
        # TODO: Document included resolvers
        # from .resolvers.cts import resolve_cts_collection_library as resolver_func
        from .resolvers.default import resolve_library as resolver_func

        return resolver_func()


class HookProxy:
    def __getattr__(self, attr):
        from .conf import settings  # noqa; avoids race condition

        return getattr(settings.SV_ATLAS_HOOKSET, attr)


hookset = HookProxy()
