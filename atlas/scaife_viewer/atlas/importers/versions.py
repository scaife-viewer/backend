import logging
import sys
from collections import defaultdict

from django.db.models import Max
from django.utils.translation import ugettext_noop

from tqdm import tqdm
from treebeard.exceptions import PathOverflow

from scaife_viewer.atlas import constants

from ..hooks import hookset
from ..models import Node
from ..urn import URN


logger = logging.getLogger(__name__)


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
        # TODO: Decouple "version_data" further
        self.urn = URN(self.version_data["urn"].strip())
        self.work_urn = self.urn.up_to(self.urn.WORK)

        try:
            label = get_first_value_for_language(version_data["label"], "eng")
        except ValueError:
            # TODO: Do we need this or can we support a fallback value above?
            label = self.work_urn
        self.label = label

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

    def get_text_group_metadata(self):
        text_group_urn = self.urn.up_to(self.urn.TEXTGROUP)
        metadata = self.library.text_groups[text_group_urn]
        label = get_first_value_for_language(metadata["name"], "eng")
        # TODO: do we actually use `lang` yet?
        extra = metadata.get("extra", {})
        return dict(label=label, **extra)

    def get_work_metadata(self):
        work_urn = self.urn.up_to(self.urn.WORK)
        metadata = self.library.works[work_urn]
        title = get_first_value_for_language(metadata["title"], "eng")
        extra = metadata.get("extra", {})
        return dict(label=title, lang=metadata["lang"], **extra)

    def get_version_metadata(self):
        default = {
            # @@@ how much of the `metadata.json` do we
            # "pass through" via GraphQL vs
            # apply to particular node kinds in the heirarchy
            "citation_scheme": self.citation_scheme,
            "label": self.label,
            "lang": self.version_data["lang"],
            "first_passage_urn": self.version_data.get("first_passage_urn"),
            "default_toc_urn": self.version_data.get("default_toc_urn"),
        }
        # TODO: how "universal" should these defaults be?
        default.update(
            dict(
                description=self.version_data["description"][0]["value"],
                kind=self.version_data["version_kind"],
                **self.version_data.get("extra", {}),
            )
        )
        return default

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

    def destructure_urn(self, node_urn, tokens, extract_text_parts=True):
        node_data = []
        for kind in self.get_urn_scheme(node_urn):
            data = {"kind": kind}

            # TODO: Determine when we're dealing with a passage reference portion vs
            # work part of the urn.
            # May be done with parts of `get_urn_scheme`
            # And maybe the "presence" / absence of tokens could help slightly too
            # @@@ duplicate; we might need a cts_ prefix for work, for example
            urn_is_work_part = (
                kind not in self.citation_scheme or kind == "work" and not tokens
            )
            if urn_is_work_part:
                data.update({"urn": self.get_partial_urn(kind, node_urn)})
                if kind == "textgroup":
                    data.update({"metadata": self.get_text_group_metadata()})
                elif kind == "work":
                    data.update({"metadata": self.get_work_metadata()})
                elif kind == "version":
                    data.update({"metadata": self.get_version_metadata()})
                # TODO: Handle exemplars
            else:
                if not extract_text_parts:
                    continue

                ref_index = self.citation_scheme.index(kind)
                ref = ".".join(node_urn.passage_nodes[: ref_index + 1])
                urn = f"{node_urn.up_to(node_urn.NO_PASSAGE)}{ref}"
                data.update({"urn": urn, "ref": ref, "rank": ref_index + 1})
                if kind == self.citation_scheme[-1]:
                    data.update({"text_content": tokens})

            node_data.append(data)

        return node_data

    def extract_urn_and_tokens(self, line):
        if not line:
            tokens = ""
            urn = f"{self.urn}"
        elif self.format == "cex":
            urn, tokens = line.strip().split("#", maxsplit=1)
        else:
            ref, tokens = line.strip().split(maxsplit=1)
            urn = f"{self.urn}{ref}"
        return URN(urn), tokens

    def generate_branch(self, line, extract_text_parts=True):
        node_urn, tokens = self.extract_urn_and_tokens(line)
        branch_data = self.destructure_urn(
            node_urn, tokens, extract_text_parts=extract_text_parts
        )
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
        if full_content_path:
            with open(full_content_path, "r") as f:
                for line in f:
                    self.generate_branch(line)
        else:
            self.generate_branch("", extract_text_parts=False)

        count = self.finalize()
        logger.debug(f"{self.label}: {count} nodes.")


def get_first_value_for_language(values, lang, fallback=True):
    # TODO: When this is called, how would we pass a fallback?
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

    library = hookset.resolve_library()

    importer_class = hookset.get_importer_class()
    nodes = {}
    for _, version_data in tqdm(library.versions.items()):
        importer_class(library, version_data, nodes).apply()
    print(f"{Node.objects.count()} total nodes on the tree.", file=sys.stderr)
