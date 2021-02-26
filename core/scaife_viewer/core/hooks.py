class DefaultHookSet:
    def sort_text_groups(self, text_groups):
        return sorted(text_groups, key=lambda tg: tg.urn)

    def sort_works(self, works):
        return sorted(works, key=lambda w: w.urn)

    def sort_texts(self, texts):
        return sorted(texts, key=lambda t: (t.kind, t.label))


class HookProxy:
    def __getattr__(self, attr):
        from .conf import settings  # noqa; avoids race condition

        return getattr(settings.SCAIFE_VIEWER_CORE_HOOKSET, attr)


hookset = HookProxy()
