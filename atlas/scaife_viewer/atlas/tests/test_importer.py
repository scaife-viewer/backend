import copy
from unittest import mock

from scaife_viewer.atlas.importers.versions import CTSImporter, Library
from scaife_viewer.atlas.tests import constants
from scaife_viewer.atlas.urn import URN


library = Library(**constants.LIBRARY_DATA)


def test_destructure():
    urn = URN("urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1")
    tokens = "Some tokens"

    assert CTSImporter(library, constants.VERSION_DATA).destructure_urn(
        urn, tokens
    ) == [
        {"kind": "nid", "urn": "urn:cts:"},
        {"kind": "namespace", "urn": "urn:cts:greekLit:"},
        {
            "kind": "textgroup",
            "urn": "urn:cts:greekLit:tlg0012:",
            "metadata": {"label": "Homer"},
        },
        {
            "kind": "work",
            "urn": "urn:cts:greekLit:tlg0012.tlg001:",
            "metadata": {"label": "Iliad"},
        },
        {
            "kind": "version",
            "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:",
            "metadata": constants.VERSION_METADATA,
        },
        {
            "kind": "book",
            "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1",
            "ref": "1",
            "rank": 1,
        },
        {
            "kind": "line",
            "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1",
            "ref": "1.1",
            "text_content": tokens,
            "rank": 2,
        },
    ]


def test_destructure_alphanumeric():
    urn = URN("urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.2.a.3")
    scheme = ["rank_1", "rank_2", "rank_3", "rank_4"]
    tokens = "Some tokens"
    version_data = copy.deepcopy(
        library.versions["urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:"]
    )
    version_data.update({"citation_scheme": scheme})
    metadata = copy.deepcopy(constants.VERSION_METADATA)
    metadata.update({"citation_scheme": scheme})

    assert CTSImporter(library, version_data).destructure_urn(urn, tokens) == [
        {"kind": "nid", "urn": "urn:cts:"},
        {"kind": "namespace", "urn": "urn:cts:greekLit:"},
        {
            "kind": "textgroup",
            "urn": "urn:cts:greekLit:tlg0012:",
            "metadata": {"label": "Homer"},
        },
        {
            "kind": "work",
            "urn": "urn:cts:greekLit:tlg0012.tlg001:",
            "metadata": {"label": "Iliad"},
        },
        {
            "kind": "version",
            "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:",
            "metadata": metadata,
        },
        {
            "kind": "rank_1",
            "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1",
            "ref": "1",
            "rank": 1,
        },
        {
            "kind": "rank_2",
            "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.2",
            "ref": "1.2",
            "rank": 2,
        },
        {
            "kind": "rank_3",
            "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.2.a",
            "ref": "1.2.a",
            "rank": 3,
        },
        {
            "kind": "rank_4",
            "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.2.a.3",
            "ref": "1.2.a.3",
            "text_content": tokens,
            "rank": 4,
        },
    ]


@mock.patch(
    "scaife_viewer.atlas.importers.versions.open",
    new_callable=mock.mock_open,
    read_data=constants.PASSAGE,
)
@mock.patch("scaife_viewer.atlas.importers.versions.CTSImporter.generate_node")
@mock.patch("scaife_viewer.atlas.importers.versions.Node")
def test_importer(mock_node, mock_generate, mock_open):
    CTSImporter(library, constants.VERSION_DATA, {}).apply()

    assert mock_generate.mock_calls == [
        mock.call(0, {"kind": "nid", "urn": "urn:cts:", "idx": 0}, None),
        mock.call(
            1, {"kind": "namespace", "urn": "urn:cts:greekLit:", "idx": 0}, "urn:cts:"
        ),
        mock.call(
            2,
            {
                "kind": "textgroup",
                "urn": "urn:cts:greekLit:tlg0012:",
                "metadata": {"label": "Homer"},
                "idx": 0,
            },
            "urn:cts:greekLit:",
        ),
        mock.call(
            3,
            {
                "kind": "work",
                "urn": "urn:cts:greekLit:tlg0012.tlg001:",
                "metadata": {"label": "Iliad"},
                "idx": 0,
            },
            "urn:cts:greekLit:tlg0012:",
        ),
        mock.call(
            4,
            {
                "kind": "version",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:",
                "metadata": {
                    "citation_scheme": ["book", "line"],
                    "label": "Iliad, Homeri Opera",
                    "lang": "grc",
                    "first_passage_urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7",
                    "default_toc_urn": None,
                },
                "idx": 0,
            },
            "urn:cts:greekLit:tlg0012.tlg001:",
        ),
        mock.call(
            5,
            {
                "kind": "book",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1",
                "ref": "1",
                "rank": 1,
                "idx": 0,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:",
        ),
        mock.call(
            6,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1",
                "ref": "1.1",
                "rank": 2,
                "text_content": "μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος",
                "idx": 0,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1",
        ),
        mock.call(
            6,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.2",
                "ref": "1.2",
                "rank": 2,
                "text_content": "οὐλομένην, ἣ μυρίʼ Ἀχαιοῖς ἄλγεʼ ἔθηκε,",
                "idx": 1,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1",
        ),
        mock.call(
            6,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.3",
                "ref": "1.3",
                "rank": 2,
                "text_content": "πολλὰς δʼ ἰφθίμους ψυχὰς Ἄϊδι προΐαψεν",
                "idx": 2,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1",
        ),
        mock.call(
            6,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.4",
                "ref": "1.4",
                "rank": 2,
                "text_content": "ἡρώων, αὐτοὺς δὲ ἑλώρια τεῦχε κύνεσσιν",
                "idx": 3,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1",
        ),
        mock.call(
            6,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.5",
                "ref": "1.5",
                "rank": 2,
                "text_content": "οἰωνοῖσί τε πᾶσι, Διὸς δʼ ἐτελείετο βουλή,",
                "idx": 4,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1",
        ),
        mock.call(
            6,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.6",
                "ref": "1.6",
                "rank": 2,
                "text_content": "ἐξ οὗ δὴ τὰ πρῶτα διαστήτην ἐρίσαντε",
                "idx": 5,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1",
        ),
        mock.call(
            6,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.7",
                "ref": "1.7",
                "rank": 2,
                "text_content": "Ἀτρεΐδης τε ἄναξ ἀνδρῶν καὶ δῖος Ἀχιλλεύς.",
                "idx": 6,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1",
        ),
    ]


@mock.patch(
    "scaife_viewer.atlas.importers.versions.open",
    new_callable=mock.mock_open,
    read_data=constants.PASSAGE,
)
@mock.patch("scaife_viewer.atlas.importers.versions.CTSImporter.generate_node")
@mock.patch("scaife_viewer.atlas.importers.versions.Node")
def test_importer_with_exemplar(mock_node, mock_generate, mock_open):
    version_urn = "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:"
    exemplar_urn = "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:"
    library_ = copy.deepcopy(library)
    exemplar_data = library_.versions.pop(version_urn)
    exemplar_data.update({"urn": exemplar_urn})
    library_.versions[exemplar_urn] = exemplar_data

    CTSImporter(library_, exemplar_data, {}).apply()

    assert mock_generate.mock_calls == [
        mock.call(0, {"kind": "nid", "urn": "urn:cts:", "idx": 0}, None),
        mock.call(
            1, {"kind": "namespace", "urn": "urn:cts:greekLit:", "idx": 0}, "urn:cts:"
        ),
        mock.call(
            2,
            {
                "kind": "textgroup",
                "urn": "urn:cts:greekLit:tlg0012:",
                "metadata": {"label": "Homer"},
                "idx": 0,
            },
            "urn:cts:greekLit:",
        ),
        mock.call(
            3,
            {
                "kind": "work",
                "urn": "urn:cts:greekLit:tlg0012.tlg001:",
                "metadata": {"label": "Iliad"},
                "idx": 0,
            },
            "urn:cts:greekLit:tlg0012:",
        ),
        mock.call(
            4,
            {
                "kind": "version",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:",
                "metadata": {
                    "citation_scheme": ["book", "line"],
                    "label": "Iliad, Homeri Opera",
                    "lang": "grc",
                    "first_passage_urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7",
                    "default_toc_urn": None,
                },
                "idx": 0,
            },
            "urn:cts:greekLit:tlg0012.tlg001:",
        ),
        mock.call(
            5,
            {
                "kind": "exemplar",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:",
                "idx": 0,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:",
        ),
        mock.call(
            6,
            {
                "kind": "book",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1",
                "ref": "1",
                "rank": 1,
                "idx": 0,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:",
        ),
        mock.call(
            7,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1.1",
                "ref": "1.1",
                "rank": 2,
                "text_content": "μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος",
                "idx": 0,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1",
        ),
        mock.call(
            7,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1.2",
                "ref": "1.2",
                "rank": 2,
                "text_content": "οὐλομένην, ἣ μυρίʼ Ἀχαιοῖς ἄλγεʼ ἔθηκε,",
                "idx": 1,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1",
        ),
        mock.call(
            7,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1.3",
                "ref": "1.3",
                "rank": 2,
                "text_content": "πολλὰς δʼ ἰφθίμους ψυχὰς Ἄϊδι προΐαψεν",
                "idx": 2,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1",
        ),
        mock.call(
            7,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1.4",
                "ref": "1.4",
                "rank": 2,
                "text_content": "ἡρώων, αὐτοὺς δὲ ἑλώρια τεῦχε κύνεσσιν",
                "idx": 3,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1",
        ),
        mock.call(
            7,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1.5",
                "ref": "1.5",
                "rank": 2,
                "text_content": "οἰωνοῖσί τε πᾶσι, Διὸς δʼ ἐτελείετο βουλή,",
                "idx": 4,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1",
        ),
        mock.call(
            7,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1.6",
                "ref": "1.6",
                "rank": 2,
                "text_content": "ἐξ οὗ δὴ τὰ πρῶτα διαστήτην ἐρίσαντε",
                "idx": 5,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1",
        ),
        mock.call(
            7,
            {
                "kind": "line",
                "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1.7",
                "ref": "1.7",
                "rank": 2,
                "text_content": "Ἀτρεΐδης τε ἄναξ ἀνδρῶν καὶ δῖος Ἀχιλλεύς.",
                "idx": 6,
            },
            "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:1",
        ),
    ]
