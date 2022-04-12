import os
import unicodedata
from collections import defaultdict
from functools import lru_cache

import anytree
import regex
from lxml import etree
from MyCapytain.common.constants import Mimetypes, XPATH_NAMESPACES
from MyCapytain.common.reference import CtsReference as Reference
from MyCapytain.common.utils import normalize

from ..conf import settings

from .capitains import default_resolver
from .reference import URN


w = r"\w[-\w]*"
p = r"\p{P}+"
ws = r"[\p{Z}\s]+"
token_re = regex.compile(fr"{w}|{p}|{ws}")
w_re = regex.compile(w)
p_re = regex.compile(p)
ws_re = regex.compile(ws)


class Passage:
    def __init__(self, text, reference):
        self.text = text
        self.reference = reference
        self.token_lookup = {}
        if not isinstance(self.reference, Reference):
            self.reference = Reference(self.reference)

    def __repr__(self):
        return f"<cts.Passage {self.urn} at {hex(id(self))}>"

    def __eq__(self, other):
        if type(other) is type(self):
            return self.text.urn == other.text.urn and self.reference == other.reference
        return NotImplemented

    def __hash__(self):
        return hash(self.urn)

    def exists(self):
        try:
            # checks start and end for existence
            self.refs
        except anytree.ChildResolverError:
            return False
        return True

    @property
    def urn(self):
        return URN(f"{self.text.urn}:{self.reference}")

    @property
    def sanitized_reference(self):
        if not settings.SCAIFE_VIEWER_CORE_NORMALIZE_SUBREFERENCES:
            return self.reference

        # NOTE: Returns a version of the reference where all
        # subreferences have been stripped
        parts = str(self.reference).split("-")
        reference = "-".join([r.split("@")[0] for r in parts])
        return Reference(reference)

    @property
    def lsb(self):
        return str(self.sanitized_reference).split(".")[-1]

    @lru_cache()
    def textual_node(self):
        # MyCapytain bug: local resolver getTextualNode can't take a Reference
        return default_resolver().getTextualNode(
            self.text.urn, subreference=str(self.sanitized_reference)
        )

    @property
    def refs(self):
        ref_range = {
            "start": self.text.toc().lookup(".".join(self.sanitized_reference.start.list))
        }
        if self.sanitized_reference.end:
            ref_range["end"] = self.text.toc().lookup(".".join(self.sanitized_reference.end.list))
        return ref_range

    def normalized_text(self, text):
        return unicodedata.normalize("NFC", text)

    def plain_text_export(self, node):
        """
        Mimics self.textual_node().export(Mimetypes.PLAINTEXT) on
        a provided Node
        """
        exclude = ""
        plaintext_string_join = " "
        return normalize(
            plaintext_string_join.join(
                [
                    element
                    for element
                    in node.xpath(
                        ".//descendant-or-self::text(){}".format(exclude),
                        namespaces=XPATH_NAMESPACES,
                        smart_strings=False
                    )
                ]
            )
        )

    def node_as_content(self, node):
        text = self.plain_text_export(node)
        return self.normalized_text(text)

    @property
    def content(self):
        text = self.textual_node().export(Mimetypes.PLAINTEXT)
        return self.normalized_text(text)

    @property
    def xml(self):
        """
        Returns the passage as XML
        """
        return self.textual_node().export(Mimetypes.XML.TEI)

    def next(self):
        reference = self.textual_node().nextId
        if reference:
            return Passage(self.text, reference)

    def prev(self):
        reference = self.textual_node().prevId
        if reference:
            return Passage(self.text, reference)

    @property
    def textpart_refs_range(self):
        """
        Returns the range of refs from self.refs
        """
        refs = [self.refs["start"]]
        if "end" in self.refs:
            for sibling in self.refs["start"].siblings:
                refs.append(sibling)
                if sibling == self.refs["end"]:
                    break
        return refs

    def get_leaf_textpart_nodes(self, citation_label=None):
        # Re-uses the refsDecl parsing from MyCapytain
        # https://github.com/Capitains/MyCapytain/blob/60e699bba291b83859fd6499b0a2b9a13b1f91d7/MyCapytain/common/reference/_capitains_cts.py#L828
        # https://github.com/Capitains/MyCapytain/blob/60e699bba291b83859fd6499b0a2b9a13b1f91d7/MyCapytain/common/reference/_capitains_cts.py#L942
        node_selector = self.textual_node().citation.fill()
        return self.textual_node().xml.xpath(node_selector, namespaces=XPATH_NAMESPACES)

    def tokenize(self, words=True, punctuation=True, whitespace=True):
        tokens = []
        idx = defaultdict(int)
        offset = 0
        passage_idx = 0

        refs_range = self.textpart_refs_range
        # citation_label = refs_range[0].label
        # leaf_nodes = self.get_leaf_textpart_nodes(citation_label)
        leaf_nodes = self.get_leaf_textpart_nodes()


        # NOTE: To populate each token's veRef (<ref>.t<1-based token position>),
        # we must iterate through each text part.
        # `self.node_as_content` should have identical output to `self.content`.
        # For the top-level text part (e.g. Book), this will produce all tokens
        # at the top-level exemplar
        for (ref, text_part_node) in zip(refs_range, leaf_nodes):
            content = self.node_as_content(text_part_node)
            text_part_position = 1
            for w in token_re.findall(content):
                if w:
                    wl = len(w)
                    if w_re.match(w):
                        offset += wl
                        if not words:
                            continue
                        t = "w"
                    if p_re.match(w):
                        offset += wl
                        if not punctuation:
                            continue
                        t = "p"
                    if ws_re.match(w):
                        if not whitespace:
                            continue
                        t = "s"
                    for wk in (w[i : j + 1] for i in range(wl) for j in range(i, wl)):
                        idx[wk] += 1
                    token = {"w": w, "i": idx[w], "t": t, "o": offset}

                    if t == "w":
                        # Set / increment passageIdx for word tokens only
                        # TODO: revisit key size; prefer for readability
                        token["passageIdx"] = passage_idx
                        token["veRef"] = f"{ref}.t{text_part_position}"
                        passage_idx += 1
                        text_part_position += 1

                    tokens.append(token)
        return tokens

    def populate_token_lookup(self, word_tokens):
        for token in word_tokens:
            self.token_lookup[token["passageIdx"]] = token["veRef"]

    def get_citations(self, citation):
        citations = []
        citations.append(citation)
        while citation.child:
            citations.append(citation.child)
            citation = citation.child
        return citations

    @lru_cache()
    def render(self):
        tn = self.textual_node()
        tei = tn.resource
        citations = self.get_citations(tn._text.citation)
        # TODO: Revisit lru_cache decorator with word_tokens; needs
        # to be hashable to pass as an arg, so we are setting it
        # in `populate_token_lookup`
        # prior to calling render
        # TODO: Determine which args are being used as the cache key here
        return TEIRenderer(tei, citations=citations, token_lookup=self.token_lookup)

    def ancestors(self):
        toc = self.text.toc()
        toc_ref = toc.lookup(str(self.sanitized_reference.start))
        for ancestor in toc_ref.ancestors[1:]:
            yield Passage(self.text, ancestor.reference)

    def children(self):
        toc = self.text.toc()
        toc_ref = toc.lookup(str(self.sanitized_reference.start))
        for child in toc_ref.children:
            yield Passage(self.text, child.reference)

    def as_json(self, with_content=True) -> dict:
        refs = {
            "start": {
                "reference": self.refs["start"].reference,
                "human_reference": self.refs["start"].human_reference,
            }
        }
        if "end" in self.refs:
            refs["end"] = {
                "reference": self.refs["end"].reference,
                "human_reference": self.refs["end"].human_reference,
            }
        o = {
            "urn": str(self.urn),
            "text": {
                "urn": str(self.text.urn),
                "label": self.text.label,
                "ancestors": [
                    {"urn": str(ancestor.urn), "label": ancestor.label}
                    for ancestor in self.text.ancestors()
                ],
                "lang": self.text.lang,
                "human_lang": self.text.human_lang,
                "kind": self.text.kind,
            },
            "refs": refs,
            "ancestors": [
                {"reference": str(ancestor.reference)} for ancestor in self.ancestors()
            ],
            "children": [
                {"reference": str(child.reference), "lsb": child.lsb}
                for child in self.children()
            ],
        }
        if with_content:
            word_tokens = self.tokenize(punctuation=False, whitespace=False)
            self.populate_token_lookup(word_tokens)
            o.update(
                {
                    "text_html": str(self.render()),
                    "word_tokens": word_tokens,
                }
            )
        return o


class TEIRenderer:
    def __init__(self, tei, citations=None, token_lookup=None):
        self.tei = tei
        self.citations = citations
        self.indexes = defaultdict(int)
        self.offset = 0
        self.passage_idx = 0

        self.node_citations_lookup = {}
        self.depth_map = {}
        self.depths = reversed(range(1, citations[0].root.depth + 1))

        if token_lookup is None:
            token_lookup = {}
        self.token_lookup = token_lookup

    def __str__(self):
        return self.render()

    @lru_cache()
    def render(self):
        xsl_path = os.path.join(os.path.dirname(__file__), settings.XSL_STYLESHEET_PATH)
        with open(xsl_path, "rb") as f:
            func_ns = "urn:python-funcs"
            transform = etree.XSLT(
                etree.XML(f.read()),
                extensions={
                    (func_ns, "is_citable_node"): self.is_citable_node,
                    (func_ns, "has_descendants"): self.has_descendants,
                    (func_ns, "cts_reference"): self.cts_reference,
                    (func_ns, "tokens"): self.tokens,
                    (func_ns, "token_type"): self.token_type,
                    (func_ns, "token_index"): self.token_index,
                    (func_ns, "token_offset"): self.token_offset,
                    (func_ns, "token_passage_idx"): self.token_passage_idx,
                    (func_ns, "token_ve_ref"): self.token_ve_ref,
                },
            )
            try:
                return str(transform(self.tei))
            except Exception:
                for error in transform.error_log:
                    print(error.message, error.line)
                raise

    def tokens(self, context, value):
        ts = []
        v = "".join(value)
        for token in token_re.findall(v):
            if token:
                ts.append(unicodedata.normalize("NFC", token))
        return ts

    def token_type(self, ctx, value):
        v = "".join(value)
        if w_re.match(v):
            self.offset += len(v)
            ctx.eval_context["is_word"] = True
            return "w"
        if p_re.match(v):
            self.offset += len(v)
            return "p"
        if ws_re.match(v):
            return "s"

    def token_offset(self, context, value):
        v = "".join(value)
        return self.offset - len(v)

    def token_index(self, context, value):
        v = "".join(value)
        lv = len(v)
        for k in (v[i : j + 1] for i in range(lv) for j in range(i, lv)):
            self.indexes[k] += 1
        return self.indexes[v]

    def token_passage_idx(self, ctx, value):
        if ctx.eval_context.get("is_word"):
            # Store the current value
            ctx.eval_context["passage_idx"] = self.passage_idx

            # Increment for the next value
            self.passage_idx += 1

            # Set `ve_ref` using passage_idx
            ctx.eval_context["ve_ref"] = self.token_lookup.get(ctx.eval_context["passage_idx"], "")

            # Return the current value
            return ctx.eval_context["passage_idx"]
        return ""

    def token_ve_ref(self, ctx, value):
        if ctx.eval_context.get("is_word"):
            # TODO: If possible, it would be better to resolve
            # the veRef from the XSLT loop
            return ctx.eval_context.pop("ve_ref", "")
        return ""

    def get_ref_nodes_subset(self, node, citation, citation_child):
        fill_args = []
        for depth in self.depths:
            value = self.depth_map.get(depth)
            if value:
                fill_args.append(value)
            else:
                fill_args.append(node.attrib["n"])
            if depth == citation.depth:
                break

        fill_args.append("")

        xpathish = citation_child.fill(fill_args).replace("@n=''", "@n")

        return node.xpath(xpathish, namespaces={"tei": "http://www.tei-c.org/ns/1.0"})

    def seed_citations_lookup(self, node, citation):
        citation_child = citation.child
        print(
            f'Seeding {citation_child.name} descendants [citation="{citation.name}" n="{node.attrib["n"]}"]'
        )

        # NOTE: Resolving the xpath to populate children actually seemed to have worse
        # performance; should compare with MyCapytain

        # ref_nodes = self.get_ref_nodes_subset(node, citation, citation_child)

        ref_nodes = node.xpath(
            citation_child.fill(), namespaces={"tei": "http://www.tei-c.org/ns/1.0"}
        )
        # NOTE: I had tried to memoize all citations, but the memory locations
        # of each node changed during XSLT processing and this resulted in a great
        # deal of cache misses
        for node in ref_nodes:
            key = node.__hash__()
            self.node_citations_lookup[key] = citation_child

    def get_citation(self, node):
        key = node.__hash__()
        citation = self.node_citations_lookup.get(key)
        if citation:
            print(f"Memoized [citation={citation.name} n={node.attrib['n']}]")
            return citation

        for citation in self.citations:
            result = node.xpath(
                citation.fill(), namespaces={"tei": "http://www.tei-c.org/ns/1.0"}
            )
            ref_nodes = set(result)
            if node in ref_nodes:
                if citation.child:
                    self.seed_citations_lookup(node, citation)
                return citation
        return

    def is_citable_node(self, ctx, value):
        # Original selector t:div[@type='textpart' and @n]|t:l
        node = value[0]
        citation = self.get_citation(node)
        if not citation:
            return

        ctx.eval_context["citation"] = citation
        return bool(citation)

    def has_descendants(self, ctx, value):
        citation = ctx.eval_context["citation"]
        if not citation:
            return False
        return bool(citation.child)

    def resolve_reference_from_citations(self, citation, node):
        citable_nodes = []
        for a_node in node.iterancestors():
            a_citation = self.get_citation(a_node)
            if a_citation:
                citable_nodes.append((a_citation, a_node))
        citable_nodes.append((citation, node))
        return ".".join([node.attrib["n"] for (_, node) in citable_nodes])

    def cts_reference(self, ctx, value):
        # TODO: Traverse via the DOM?
        # traverse up looking for parent elements on click (or on render if we really need to....)
        target_node = value[0]
        citation = ctx.eval_context["citation"]
        self.depth_map[citation.depth] = target_node.attrib["n"]
        # TODO: This assumes things are sequential; we had places in Digital Sira
        #  where they were assuredly _not_
        parts = []
        for depth in self.depths:
            parts.append(self.depth_map.get(depth))
            if depth == citation.depth:
                break
        return ".".join(parts)
