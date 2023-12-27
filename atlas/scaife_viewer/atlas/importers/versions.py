import logging
from collections import defaultdict

from django.db import IntegrityError
from django.utils.translation import ugettext_noop

from tqdm import tqdm
from treebeard.exceptions import PathOverflow

from scaife_viewer.atlas import constants

from ..hooks import hookset
from ..models import Node
from ..urn import URN
from ..utils import chunked_bulk_create, get_lowest_citable_depth


logger = logging.getLogger(__name__)

"""
`Node.save` performs multiple INSERT and UPDATE queries.

For text-part level nodes, we see a massive performance
benefit by batching and bulk inserting the nodes. This is
also true for corpora with hundreds of work-part level nodes.

Overriding `get_descendants` and `get_children` to use
"live" queries allows us to skip manually setting the
`numchild` value of of each node.

Skipping the queries needed to set `numchild` speeds up
ingestion time by 180% on a test data set (64 seconds vs
184 seconds on one test dataset).
"""
USE_BULK_INGESTION = True


class CTSImporter:
    """
    urn:cts:CTSNAMESPACE:WORK:PASSAGE
    https://cite-architecture.github.io/ctsurn_spec
    """

    CTS_URN_SCHEME = constants.CTS_URN_NODES[:-1]
    CTS_URN_SCHEME_EXEMPLAR = constants.CTS_URN_NODES

    def __init__(
        self, library, version_data, nodes=dict(), node_last_child_lookup=None
    ):
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
        self.lowest_citable_depth = get_lowest_citable_depth(self.citation_scheme)
        self.idx_lookup = defaultdict(int)

        self.nodes_to_create = []

        if node_last_child_lookup is None:
            node_last_child_lookup = defaultdict()
        self.node_last_child_lookup = node_last_child_lookup
        self.format = version_data.get("format", "txt")
        # TODO: Provide a better interface here
        self.textpart_metadata = self.version_data.get("textpart_metadata", {})

    @staticmethod
    def add_root(data):
        return Node.add_root(**data)

    @staticmethod
    def add_child(parent, data):
        try:
            return parent.add_child(**data)
        except IntegrityError:
            # TODO: Make this a specific option _only_ when ingesting
            # a portion of the corpus
            return Node.objects.get(urn=data["urn"])

    @staticmethod
    def check_depth(path):
        return len(path) > Node._meta.get_field("path").max_length

    @staticmethod
    def get_parent_urn(idx, branch_data):
        return branch_data[idx - 1]["urn"] if idx else None

    def get_node_idx(self, node_data):
        key = node_data["kind"]
        rank = node_data.get("rank")
        if rank:
            key = f"{rank}_{key}"
        idx = self.idx_lookup[key]
        self.idx_lookup[key] += 1
        return idx

    def get_partial_urn(self, workpart_kind, node_urn):
        scheme = self.get_root_urn_scheme(node_urn)
        kind_map = {kind: getattr(URN, kind.upper()) for kind in scheme}
        return node_urn.up_to(kind_map[workpart_kind])

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

    def get_textpart_metadata(self, urn):
        return self.textpart_metadata.get(urn) or {}

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

    def generate_node(self, idx, node_data, parent_urn):
        if idx == 0:
            try:
                return self.add_root(node_data)
            except IntegrityError:
                # TODO: As above, only swallow this exception
                # when doing a partial ingestion
                return Node.objects.get(urn=node_data["urn"])
        parent = self.nodes.get(parent_urn)
        if USE_BULK_INGESTION:
            return self.add_child_bulk(parent, node_data)
        return self.add_child(parent, node_data)

    @staticmethod
    def is_workpart(value):
        # TODO: Support exemplars
        return value <= constants.CTS_URN_DEPTHS["version"]

    def destructure_urn(self, node_urn, text_content):
        node_data = []
        for pos, kind in enumerate(self.get_urn_scheme(node_urn)):
            depth = pos + 1
            data = {"kind": kind}
            is_workpart = self.is_workpart(depth)
            if is_workpart:
                data.update({"urn": self.get_partial_urn(kind, node_urn)})
                if kind == "textgroup":
                    data.update({"metadata": self.get_text_group_metadata()})
                elif kind == "work":
                    data.update({"metadata": self.get_work_metadata()})
                elif kind == "version":
                    data.update({"metadata": self.get_version_metadata()})
                # TODO: Handle exemplars
            else:
                # NOTE: `text_content is None` allows for empty text parts
                if text_content is None and not self.textpart_metadata:
                    continue

                ref_index = self.citation_scheme.index(kind)
                ref = ".".join(node_urn.passage_nodes[: ref_index + 1])
                urn = f"{node_urn.up_to(node_urn.NO_PASSAGE)}{ref}"
                rank = ref_index + 1
                data.update({"urn": urn, "ref": ref, "rank": rank})

                if depth == self.lowest_citable_depth:
                    data.update({"text_content": text_content})
                if rank == 1:
                    # TODO: Additive metadata, other ranks
                    data.update({"metadata": self.get_textpart_metadata(urn)})

            node_data.append(data)

        return node_data

    def extract_urn_and_text_content(self, line):
        if self.format == "cex":
            urn, text_content = line.strip().split("#", maxsplit=1)
        else:
            ref, text_content = line.strip().split(maxsplit=1)
            urn = f"{self.urn}{ref}"
        return URN(urn), text_content

    def generate_branch(self, urn=None, line=None):
        if line:
            node_urn, text_content = self.extract_urn_and_text_content(line)
        elif urn:
            node_urn = urn
            text_content = None
        else:
            raise ValueError('Either a "urn" or "line" value must be supplied.')

        branch_data = self.destructure_urn(node_urn, text_content)
        for idx, node_data in enumerate(branch_data):
            node = self.nodes.get(node_data["urn"])
            if node is None:
                node_data.update({"idx": self.get_node_idx(node_data)})
                parent_urn = self.get_parent_urn(idx, branch_data)
                node = self.generate_node(idx, node_data, parent_urn)
                self.nodes[node_data["urn"]] = node

    def apply(self):
        full_content_path = self.library.versions[self.urn.absolute]["path"]
        if full_content_path:
            with open(full_content_path, "r") as f:
                for line in f:
                    self.generate_branch(line=line)
        elif self.textpart_metadata:
            # NOTE: This allows SV 1 readers to ingest text parts
            # without needing to also ingest text_content or tokens
            for urn in self.textpart_metadata.keys():
                self.generate_branch(urn=URN(urn))
        else:
            self.generate_branch(urn=self.urn)
        return self.nodes_to_create


def get_first_value_for_language(values, lang, fallback=True):
    # TODO: When this is called, how would we pass a fallback?
    value = next(iter(filter(lambda x: x["lang"] == lang, values)), None)
    if value is None:
        if fallback:
            value = values[0]
        else:
            raise ValueError(f"Could not find a value for {lang}")
    return value.get("value")


def import_versions(reset=False, predicate=None):
    if reset:
        Node.objects.filter(kind="nid").delete()
    # TODO: Wire up logging
    logger.info("Resolving library")
    library = hookset.resolve_library()

    logger.info("Building Node tree")
    importer_class = hookset.get_importer_class()
    nodes = {}

    to_ingest = list(library.versions.values())

    if predicate:
        """
        Suggested usage:
        predicate = lambda x: x["urn"] == "urn:cts:greekLit:tlg0012.tlg001.parrish-eng1:"
        from scaife_viewer.atlas.importers.versions import *
        import_versions(predicate=predicate)
        """
        to_ingest = filter(predicate, to_ingest)

    to_defer = []
    lookup = None

    # NOTE: We don't know the number of individual nodes; we could also
    # report on the number of versions, but for now, I thought a Node
    # counter from tqdm would be more useful.
    with tqdm() as pbar:
        for version_data in to_ingest:
            importer = importer_class(library, version_data, nodes, lookup)
            deferred_nodes = importer.apply()

            to_defer.extend(deferred_nodes)
            count = len(deferred_nodes)
            pbar.update(count)
            logger.debug(f"{importer.label}: {count} nodes.")

            lookup = importer.node_last_child_lookup

    logger.info("Inserting Node tree")
    chunked_bulk_create(Node, to_defer)
    logger.info(f"{Node.objects.count()} total nodes on the tree.")
