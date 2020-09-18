"""
@@@ prepare for ingestion;
"""
import json

import conllu


def main():
    # FIXME: Need to add conllu to deps
    path = "grc_perseus-ud-perseus-grc2.conllu"
    data = conllu.parse(open(path).read())

    version = "urn:cts:greekLit:tlg0085.tlg001.perseus-grc2:"
    meta = {}
    to_create = []
    counter = 0
    for sentence in data:
        counter += 1
        meta.update(sentence.metadata)
        new_obj = {}
        new_obj.update(meta)

        seen_urns = set()
        sentence_id = int(new_obj["sent_id"].split("@")[1])

        sentence_obj = {
            "urn": f"urn:cite2:exploreHomer:syntaxTree.v1:syntaxTree{sentence_id}",
            "treebank_id": sentence_id,
            "words": [],
        }
        for token in sentence:
            word_obj = {
                "id": token["id"],
                "value": token["form"],
                "head_id": token["head"],
                "relation": token["deprel"],
            }
            sentence_obj["words"].append(word_obj)

        # TODO: can't do cite or refs just yet, which will be required
        # This is likely something we could do from that sent_id as another
        # kind of lookup
        sentence_obj.update(
            {"references": [], "citation": str(sentence_id),}
        )
        to_create.append(sentence_obj)

    json.dump(
        to_create,
        open("syntax_trees_tlg0085.tlg001.perseus-grc2.json", "w"),
        ensure_ascii=False,
        indent=2,
    )


if __name__ == "__main__":
    main()
