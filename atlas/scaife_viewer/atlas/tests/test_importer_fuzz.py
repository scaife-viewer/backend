import copy

import hypothesis
from scaife_viewer.atlas.importers.versions import CTSImporter, Library
from scaife_viewer.atlas.tests.strategies import URNs
from scaife_viewer.atlas.urn import URN


def _get_library(urn):
    textgroup_urn = urn.up_to(urn.TEXTGROUP)
    work_urn = urn.up_to(urn.WORK)
    version_urn = urn.up_to(urn.VERSION)
    library_data = {
        "text_groups": {
            textgroup_urn: {
                "urn": textgroup_urn,
                "node_kind": "textgroup",
                "name": [{"lang": "eng", "value": "Some Textgroup"}],
            }
        },
        "works": {
            work_urn: {
                "urn": work_urn,
                "groupUrn": textgroup_urn,
                "node_kind": "work",
                "lang": "grc",
                "title": [{"lang": "eng", "value": "Some Title"}],
                "versions": [
                    {
                        "urn": version_urn,
                        "node_kind": "version",
                        "version_kind": "edition",
                        "lang": "grc",
                        "first_passage_urn": f"{version_urn}1.1-1.5",
                        "citation_scheme": None,
                        "title": [{"lang": "eng", "value": "Some Title"}],
                        "description": [{"lang": "eng", "value": "Some description."}],
                    }
                ],
            }
        },
        "versions": {
            version_urn: {
                "urn": version_urn,
                "node_kind": "version",
                "version_kind": "edition",
                "lang": "grc",
                "first_passage_urn": f"{version_urn}1.1-1.5",
                "citation_scheme": None,
                "label": [{"lang": "eng", "value": "Some Title"}],
                "description": [{"lang": "eng", "value": "Some description."}],
            }
        },
    }
    return Library(**copy.deepcopy(library_data))


@hypothesis.given(URNs.cts_urns().map(URN))
def test_destructure(urn):
    tokens = "Some tokens"
    scheme = [f"rank_{idx + 1}" for idx, _ in enumerate(urn.passage.split("."))]
    library = _get_library(urn)
    version_data = library.versions[urn.up_to(urn.VERSION)]
    version_data.update({"citation_scheme": scheme})

    nodes = CTSImporter(library, version_data).destructure_urn(urn, tokens)

    if urn.has_exemplar:
        assert len(nodes) - len(urn.passage_nodes) == 6
    else:
        assert len(nodes) - len(urn.passage_nodes) == 5

    for idx, node in enumerate(nodes):
        if "rank" not in node:
            assert node["urn"] == urn.up_to(getattr(urn, node["kind"].upper()))
            if node["kind"] == "version":
                assert node["metadata"]["citation_scheme"] == scheme
        else:
            ref = node["ref"]
            assert node["urn"] == f"{urn.up_to(urn.NO_PASSAGE)}{ref}"
            assert node["rank"] == len(ref.split("."))
            assert node["kind"] == scheme[node["rank"] - 1]
            if node["rank"] > 1:
                assert ref.startswith(f"{nodes[idx - 1]['ref']}.")

        if idx != nodes.index(nodes[-1]):
            assert "text_content" not in node
        else:
            assert node["text_content"] == tokens
