"""
@@@ prepare for ingestion;
"""
import json
import re

from lxml import etree

from scaife_viewer.atlas.backports.scaife_viewer.cts.utils import natural_keys
from scaife_viewer.atlas.urn import URN


def main():
    with open("gorman-plato.xml") as f:
        tree = etree.parse(f)

    version = "urn:cts:greekLit:tlg0059.tlg002.perseus-grc2:"
    to_create = []
    counter = 0
    for sentence in tree.xpath(f"//sentence"):
        counter += 1
        seen_urns = set()
        sentence_obj = {
            "urn": f'urn:cite2:exploreHomer:syntaxTree.v1:syntaxTree{sentence.attrib["id"]}',
            "treebank_id": int(sentence.attrib["id"]),
            "words": [],
        }
        for word in sentence.xpath(".//word"):
            word_obj = {
                "id": int(word.attrib["id"]),
                "value": word.attrib["form"],
                "head_id": int(word.attrib["head"]),
                "relation": word.attrib["relation"],
            }
            sentence_obj["words"].append(word_obj)

            # TODO: Consider constructing URNs from document_id
            # cite = word.attrib.get("cite")
            # if cite:
            #     ref = cite.rsplit(":", maxsplit=1)[1]
            #     seen_urns.add(f"{version}{ref}")
            subdoc = sentence.attrib.get("subdoc")
            if subdoc:
                ref = re.match(r"\d+", subdoc).group()
                seen_urns.add(f"{version}{ref}")

        references = sorted(seen_urns, key=lambda x: natural_keys(x))
        sentence_obj["references"] = references
        # TODO: Resolve citation; for now, we'll just use the subdoc
        # citation = ""
        # if references:
        #     citation = URN(references[0]).passage
        #     if len(references) > 1:
        #         citation = f"{citation}-{URN(references[-1]).passage}"
        sentence_obj.update(
            {"references": references, "citation": subdoc,}
        )

        to_create.append(sentence_obj)

    json.dump(
        to_create,
        open("syntax_trees_tlg0059.tlg002.perseus-grc2.json", "w"),
        ensure_ascii=False,
        indent=2,
    )


if __name__ == "__main__":
    main()
