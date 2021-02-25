import json
import os

from scaife_viewer.atlas.conf import settings

from .common import Library


LIBRARY_DATA_PATH = os.path.join(settings.SV_ATLAS_DATA_DIR, "library")


class LibraryDataResolver:
    def __init__(self, data_dir_path):
        self.text_groups = {}
        self.works = {}
        self.versions = {}
        self.resolved = self.resolve_data_dir_path(data_dir_path)

    def populate_versions(self, dirpath, data):
        for version in data:
            version_part = version["urn"].rsplit(":", maxsplit=2)[1]

            if version.get("format") == "cex":
                extension = "cex"
            else:
                extension = "txt"

            version_path = os.path.join(dirpath, f"{version_part}.{extension}")
            if not os.path.exists(version_path):
                raise FileNotFoundError(version_path)

            self.versions[version["urn"]] = {
                **version,
                "format": extension,
                "path": version_path,
            }

    def resolve_data_dir_path(self, data_dir_path):
        for dirpath, dirnames, filenames in sorted(os.walk(data_dir_path)):
            if "metadata.json" not in filenames:
                continue

            metadata = json.load(open(os.path.join(dirpath, "metadata.json")))
            assert metadata["node_kind"] in ["textgroup", "work"]

            if metadata["node_kind"] == "textgroup":
                self.text_groups[metadata["urn"]] = metadata
            elif metadata["node_kind"] == "work":
                self.works[metadata["urn"]] = metadata
                self.populate_versions(dirpath, metadata["versions"])

        return self.text_groups, self.works, self.versions


def resolve_library():
    text_groups, works, versions = LibraryDataResolver(LIBRARY_DATA_PATH).resolved
    return Library(text_groups, works, versions)
