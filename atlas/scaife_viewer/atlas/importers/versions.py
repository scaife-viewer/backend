import json
import os
import sys
from collections import defaultdict

from django.conf import settings
from django.db.models import Max
from django.utils.translation import ugettext_noop

from treebeard.exceptions import PathOverflow

from scaife_viewer.atlas import constants

from ..models import Node
from ..urn import URN


LIBRARY_DATA_PATH = os.path.join(settings.ATLAS_CONFIG["DATA_DIR"], "library")


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
                "format": extension,
                "path": version_path,
                **version,
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


class Library:
    def __init__(self, text_groups, works, versions):
        self.text_groups = text_groups
        self.works = works
        self.versions = versions


class CTSImporter:
    """
    urn:cts:CTSNAMESPACE:WORK:PASSAGE
    https://cite-architecture.github.io/ctsurn_spec
    """

    CTS_URN_SCHEME = constants.CTS_URN_NODES[:-1]
    CTS_URN_SCHEME_EXEMPLAR = constants.CTS_URN_NODES

    def __init__(self, library, version_data, nodes=dict()):
        self.library = library
        self.version_data = version_data
        self.nodes = nodes
        self.urn = URN(self.version_data["urn"].strip())
        self.work_urn = self.urn.up_to(self.urn.WORK)
        self.label = get_first_value_for_language(version_data["label"], "eng")
        self.citation_scheme = self.version_data["citation_scheme"]
        self.idx_lookup = defaultdict(int)

        self.nodes_to_create = []
        self.node_last_child_lookup = defaultdict()
        self.format = version_data.get("format", "txt")

    @staticmethod
    def add_root(data):
        return Node.add_root(**data)

    @staticmethod
    def add_child(parent, data):
        return parent.add_child(**data)

    @staticmethod
    def check_depth(path):
        return len(path) > Node._meta.get_field("path").max_length

    @staticmethod
    def set_numchild(node):
        # @@@ experiment with F expressions
        # @@@ experiment with path__range queries
        node.numchild = Node.objects.filter(
            path__startswith=node.path, depth=node.depth + 1
        ).count()

    @staticmethod
    def get_parent_urn(idx, branch_data):
        return branch_data[idx - 1]["urn"] if idx else None

    def get_node_idx(self, kind):
        idx = self.idx_lookup[kind]
        self.idx_lookup[kind] += 1
        return idx

    def get_partial_urn(self, kind, node_urn):
        scheme = self.get_root_urn_scheme(node_urn)
        kind_map = {kind: getattr(URN, kind.upper()) for kind in scheme}
        return node_urn.up_to(kind_map[kind])

    def get_root_urn_scheme(self, node_urn):
        if node_urn.has_exemplar:
            return self.CTS_URN_SCHEME_EXEMPLAR
        return self.CTS_URN_SCHEME

    def get_urn_scheme(self, node_urn):
        return [*self.get_root_urn_scheme(node_urn), *self.citation_scheme]

    def get_textgroup_metadata(self, urn):
        metadata = self.library.text_groups[urn.up_to(URN.TEXTGROUP)]
        return {"label": get_first_value_for_language(metadata["name"], "eng")}

    def get_work_metadata(self, urn):
        metadata = self.library.works[urn.up_to(URN.WORK)]
        return {"label": get_first_value_for_language(metadata["title"], "eng")}

    def get_version_metadata(self):
        return {
            # @@@ how much of the `metadata.json` do we
            # "pass through" via GraphQL vs
            # apply to particular node kinds in the heirarchy
            "citation_scheme": self.citation_scheme,
            "label": self.label,
            "lang": self.version_data["lang"],
            "first_passage_urn": self.version_data["first_passage_urn"],
            "default_toc_urn": self.version_data.get("default_toc_urn"),
        }

    def add_child_bulk(self, parent, node_data):
        # @@@ forked version of `Node._inc_path`
        # https://github.com/django-treebeard/django-treebeard/blob/master/treebeard/mp_tree.py#L1121
        child_node = Node(**node_data)
        child_node.depth = parent.depth + 1

        last_child = self.node_last_child_lookup.get(parent.urn)
        if not last_child:
            # The node had no children, adding the first child.
            child_node.path = Node._get_path(parent.path, child_node.depth, 1)
            if self.check_depth(child_node.path):
                raise PathOverflow(
                    ugettext_noop(
                        "The new node is too deep in the tree, try"
                        " increasing the path.max_length property"
                        " and UPDATE your database"
                    )
                )
        else:
            # Adding the new child as the last one.
            child_node.path = last_child._inc_path()
        self.node_last_child_lookup[parent.urn] = child_node
        self.nodes_to_create.append(child_node)
        return child_node

    def use_bulk(self, node_data):
        """
        `Node.save` performs multiple INSERT and UPDATE queries.

        For text-part level nodes, we see a massive performance
        benefit by batching and bulk inserting the nodes, and then
        bulk updating any parent nodes to keep the `numchild`
        value of nodes in sync.
        """
        return bool(node_data.get("rank"))

    def generate_node(self, idx, node_data, parent_urn):
        if idx == 0:
            return self.add_root(node_data)
        parent = self.nodes.get(parent_urn)
        if self.use_bulk(node_data):
            return self.add_child_bulk(parent, node_data)
        return self.add_child(parent, node_data)

    def destructure_urn(self, node_urn, tokens):
        node_data = []
        for kind in self.get_urn_scheme(node_urn):
            data = {"kind": kind}

            if kind not in self.citation_scheme:
                data.update({"urn": self.get_partial_urn(kind, node_urn)})
                if kind == "textgroup":
                    data.update({"metadata": self.get_textgroup_metadata(node_urn)})
                elif kind == "work":
                    data.update({"metadata": self.get_work_metadata(node_urn)})
                elif kind == "version":
                    data.update({"metadata": self.get_version_metadata()})
            else:
                ref_index = self.citation_scheme.index(kind)
                ref = ".".join(node_urn.passage_nodes[: ref_index + 1])
                urn = f"{node_urn.up_to(node_urn.NO_PASSAGE)}{ref}"
                data.update({"urn": urn, "ref": ref, "rank": ref_index + 1})
                if kind == self.citation_scheme[-1]:
                    data.update({"text_content": tokens})

            node_data.append(data)

        return node_data

    def extract_urn_and_tokens(self, line):
        if self.format == "cex":
            urn, tokens = line.strip().split("#", maxsplit=1)
        else:
            ref, tokens = line.strip().split(maxsplit=1)
            urn = f"{self.urn}{ref}"
        return URN(urn), tokens

    def generate_branch(self, line):
        node_urn, tokens = self.extract_urn_and_tokens(line)
        branch_data = self.destructure_urn(node_urn, tokens)
        for idx, node_data in enumerate(branch_data):
            node = self.nodes.get(node_data["urn"])
            if node is None:
                node_data.update({"idx": self.get_node_idx(node_data["kind"])})
                parent_urn = self.get_parent_urn(idx, branch_data)
                node = self.generate_node(idx, node_data, parent_urn)
                self.nodes[node_data["urn"]] = node

    def update_numchild_values(self):
        self.set_numchild(self.version_node)
        to_update = [self.version_node]

        # once `numchild` is set on version, we can get descendants
        descendants = self.version_node.get_descendants()
        max_depth = descendants.all().aggregate(max_depth=Max("depth"))["max_depth"]
        for node in descendants.exclude(depth=max_depth):
            self.set_numchild(node)
            to_update.append(node)
        Node.objects.bulk_update(to_update, ["numchild"], batch_size=500)

    def finalize(self):
        self.version_node = Node.objects.get(urn=self.urn.absolute)
        Node.objects.bulk_create(self.nodes_to_create, batch_size=500)
        self.update_numchild_values()
        return self.version_node.get_descendant_count() + 1

    def apply(self):
        full_content_path = self.library.versions[self.urn.absolute]["path"]
        with open(full_content_path, "r") as f:
            for line in f:
                self.generate_branch(line)

        count = self.finalize()
        print(f"{self.label}: {count} nodes.", file=sys.stderr)


def resolve_library():
    text_groups, works, versions = LibraryDataResolver(LIBRARY_DATA_PATH).resolved
    return Library(text_groups, works, versions)


def get_first_value_for_language(values, lang, fallback=True):
    value = next(iter(filter(lambda x: x["lang"] == lang, values)), None)
    if value is None:
        if fallback:
            value = values[0]
        else:
            raise ValueError(f"Could not find a value for {lang}")
    return value.get("value")


def import_versions(reset=False):
    if reset:
        Node.objects.filter(kind="nid").delete()

    library = resolve_library()

    nodes = {}
    for _, version_data in library.versions.items():
        CTSImporter(library, version_data, nodes).apply()
    print(f"{Node.objects.count()} total nodes on the tree.", file=sys.stderr)
