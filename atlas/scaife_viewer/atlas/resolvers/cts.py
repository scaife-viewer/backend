from .common import Library
from ..hooks import hookset


class CTSCollectionResolver:
    def __init__(self, text_inventory):
        self.text_groups = {}
        self.works = {}
        self.versions = {}
        self.resolved = self.resolve_text_inventory(text_inventory)

    def resolve_versions(self, work):
        for version in work.texts():
            version_metadata = hookset.extract_cts_version_metadata(version)
            # version_urn is required within CTSImporter
            version_urn = version_metadata["urn"]
            # TODO: More validation around "path"
            version_metadata["path"] = None
            self.versions[version_urn] = version_metadata

    def resolve_works(self, text_group):
        for work in text_group.works():
            if work.urn.count(" ") > 0:
                # @@@ defensive coding around bad URNs
                continue
            work_metadata = hookset.extract_cts_work_metadata(work)
            work_urn = work_metadata.pop("urn")
            self.works[work_urn] = work_metadata
            self.resolve_versions(work)

    def resolve_text_inventory(self, text_inventory):
        """
        Resolves the library from `cts.TextInventory`.

        Since Node instances are ordered by their `path` value,
        `cts.collections.SORT_OVERRIDES` is respected by ATLAS.
        """
        for text_group in text_inventory.text_groups():
            text_group_metadata = hookset.extract_cts_text_group_metadata(text_group)
            tg_urn = text_group_metadata.pop("urn")
            self.text_groups[tg_urn] = text_group_metadata
            self.resolve_works(text_group)
        return self.text_groups, self.works, self.versions


def resolve_cts_collection_library(text_inventory, resolver_class=None):
    if resolver_class is None:
        resolver_class = CTSCollectionResolver

    text_groups, works, versions = resolver_class(text_inventory).resolved
    return Library(text_groups, works, versions)
