import re

from .common import Library


def get_lang_value(value):
    if re.match(r"^[a-z]+-[A-Z][a-z]+$", value):
        return value.split("-")[0]
    else:
        return value


class CTSCollectionResolver:
    def __init__(self, text_inventory):
        self.text_groups = {}
        self.works = {}
        self.versions = {}
        self.resolved = self.resolve_text_inventory(text_inventory)

    def extract_text_group_metadata(self, text_group):
        """
            {
                "urn": "urn:cts:greekLit:tlg0012:",
                "node_kind": "textgroup",
                "name": [
                    {
                    "lang": "eng",
                    "value": "Homer"
                    }
                ]
            }
        """
        return dict(
            urn=f"{text_group.urn}:",
            node_kind="textgroup",
            name=[dict(lang="eng", value=str(text_group.label))],
            meta_=text_group.structured_metadata(),
        )

    def extract_work_metadata(self, work):
        """
            {
                "urn": "urn:cts:greekLit:tlg0012.tlg001:",
                "group_urn": "urn:cts:greekLit:tlg0012:",
                "node_kind": "work",
                "lang": "grc",
                "title": [
                    {
                    "lang": "eng",
                    "value": "Iliad"
                    }
                ],
                "versions": [
                    {
                    "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:",
                    "node_kind": "version",
                    "version_kind": "edition",
                    "first_passage_urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7",
                    "citation_scheme": ["book", "line"],
                    "label": [
                        {
                        "lang": "eng",
                        "value": "Iliad (Greek Text of Munro & Allen)"
                        }
                    ],
                    "description": [
                        {
                        "lang": "eng",
                        "value": "Homer, creator; Monro, D. B. (David Binning), 1836-1905, creator; Monro, D. B. (David Binning), 1836-1905, editor; Allen, Thomas W. (Thomas William), b. 1862, editor"
                        }
                    ]
                    }
                ]
            }
        """
        return dict(
            urn=f"{work.urn}:",
            # @@@
            group_urn=f'{work.urn.rsplit(".", maxsplit=1)[0]}:',
            node_kind="work",
            lang=get_lang_value(work.metadata.lang),
            # @@@ label vs title wa
            title=[
                {
                    # @@@ hacky
                    "lang": work.label._language,
                    "value": str(work.label),
                }
            ],
        )

    def extract_version_metadata(self, version):
        return dict(
            urn=f"{version.urn}:",
            node_kind="version",
            version_kind=version.kind,
            # @@@
            # first_passage_urn
            citation_scheme=[c.name for c in version.metadata.citation],
            label=[
                {
                    # @@@ hacky
                    "lang": version.label._language,
                    "value": str(version.label),
                }
            ],
            description=[
                {
                    # @@@ hacky
                    "lang": version.description._language,
                    "value": str(version.description),
                }
            ],
            lang=get_lang_value(version.metadata.lang),
            tracking_title=str(version.tracking_title),
            image=version.image,
        )

    def resolve_versions(self, work):
        """
        {
        "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:",
        "node_kind": "version",
        "version_kind": "edition",
        "first_passage_urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7",
        "citation_scheme": ["book", "line"],
        "label": [
            {
            "lang": "eng",
            "value": "Iliad (Greek Text of Munro & Allen)"
            }
        ],
        "description": [
            {
            "lang": "eng",
            "value": "Homer, creator; Monro, D. B. (David Binning), 1836-1905, creator; Monro, D. B. (David Binning), 1836-1905, editor; Allen, Thomas W. (Thomas William), b. 1862, editor"
            }
        ]
        }
        """
        for version in work.texts():
            version_metadata = self.extract_version_metadata(version)
            # TODO: More validation around "path"
            version_metadata["path"] = None
            self.versions[version_metadata["urn"]] = version_metadata

    def resolve_works(self, text_group):
        for work in text_group.works():
            if work.urn.count(" ") > 0:
                # @@@ defensive coding around bad URNs
                continue
            work_metadata = self.extract_work_metadata(work)
            self.works[work_metadata["urn"]] = work_metadata
            self.resolve_versions(work)

    def resolve_text_inventory(self, text_inventory):
        """
        Resolves the library from `cts.TextInventory`.

        Since Node instances are ordered by their `path` value,
        `cts.collections.SORT_OVERRIDES` is respected by ATLAS.
        """
        for text_group in text_inventory.text_groups():
            text_group_metadata = self.extract_text_group_metadata(text_group)
            self.text_groups[text_group_metadata["urn"]] = text_group_metadata
            self.resolve_works(text_group)
        return self.text_groups, self.works, self.versions


def resolve_cts_collection_library(text_inventory):
    # TODO: Document text_inventory typing
    # TODO: consider a hookset
    text_groups, works, versions = CTSCollectionResolver(text_inventory).resolved
    return Library(text_groups, works, versions)
