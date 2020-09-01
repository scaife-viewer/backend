"""
@@@ prepare for ingestion;
"""
import json

from lxml import etree


def main():
    with open("tlg0012.tlg001.perseus-grc1.tb.xml") as f:
        tree = etree.parse(f)
    version = "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:"
    to_create = []
    for sentence in tree.xpath(f"//sentence[@subdoc='1.1-1.7']"):
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
            cite = word.attrib["cite"]
            if cite:
                ref = cite.rsplit(":", maxsplit=1)[1]
                seen_urns.add(f"{version}{ref}")
            sentence_obj["words"].append(word_obj)
        sentence_obj["references"] = sorted(list(seen_urns))
        to_create.append(sentence_obj)

    json.dump(
        to_create,
        open("syntax_trees_tlg0012.tlg001.perseus-grc2.json", "w"),
        ensure_ascii=False,
        indent=2,
    )


if __name__ == "__main__":
    main()
