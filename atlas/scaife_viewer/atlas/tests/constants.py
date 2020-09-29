TREE_DATA = [
    {
        "data": {"urn": "urn:1:", "kind": "node"},
        "children": [
            {
                "data": {"urn": "urn:11:", "kind": "node"},
                "children": [
                    {
                        "data": {"urn": "urn:111:", "kind": "node"},
                        "children": [
                            {"data": {"urn": "urn:1111:", "kind": "node", "rank": 1}}
                        ],
                    },
                    {
                        "data": {"urn": "urn:112:", "kind": "node"},
                        "children": [
                            {"data": {"urn": "urn:1121:", "kind": "node", "rank": 1}}
                        ],
                    },
                ],
            },
            {
                "data": {"urn": "urn:12:", "kind": "node"},
                "children": [
                    {
                        "data": {"urn": "urn:121:", "kind": "node"},
                        "children": [
                            {"data": {"urn": "urn:1211:", "kind": "node", "rank": 1}}
                        ],
                    },
                ],
            },
        ],
    },
]


# fmt: off
PASSAGE = """
    1.1 μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος
    1.2 οὐλομένην, ἣ μυρίʼ Ἀχαιοῖς ἄλγεʼ ἔθηκε,
    1.3 πολλὰς δʼ ἰφθίμους ψυχὰς Ἄϊδι προΐαψεν
    1.4 ἡρώων, αὐτοὺς δὲ ἑλώρια τεῦχε κύνεσσιν
    1.5 οἰωνοῖσί τε πᾶσι, Διὸς δʼ ἐτελείετο βουλή,
    1.6 ἐξ οὗ δὴ τὰ πρῶτα διαστήτην ἐρίσαντε
    1.7 Ἀτρεΐδης τε ἄναξ ἀνδρῶν καὶ δῖος Ἀχιλλεύς.
""".strip("\n")
# fmt: on


VERSION_DATA = {
    "path": "data/library/tlg0012/tlg001/tlg0012.tlg001.perseus-grc2.txt",
    "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:",
    "node_kind": "version",
    "version_kind": "edition",
    "lang": "grc",
    "first_passage_urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7",
    "citation_scheme": ["book", "line"],
    "label": [{"lang": "eng", "value": "Iliad, Homeri Opera"}],
    "description": [
        {
            "lang": "eng",
            "value": "Homer, creator; Monro, D. B. (David Binning), 1836-1905, creator; Monro, D. B. (David Binning), 1836-1905, editor; Allen, Thomas W. (Thomas William), b. 1862, editor",
        }
    ],
}

VERSION_METADATA = {
    "citation_scheme": ["book", "line"],
    "label": "Iliad, Homeri Opera",
    "lang": "grc",
    "first_passage_urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7",
    "description": "Homer, creator; Monro, D. B. (David Binning), 1836-1905, creator; Monro, D. B. (David Binning), 1836-1905, editor; Allen, Thomas W. (Thomas William), b. 1862, editor",
    "kind": "edition",
    "default_toc_urn": None,
}
LIBRARY_DATA = {
    "text_groups": {
        "urn:cts:greekLit:tlg0012:": {
            "urn": "urn:cts:greekLit:tlg0012:",
            "node_kind": "textgroup",
            "name": [{"lang": "eng", "value": "Homer"}],
        }
    },
    "works": {
        "urn:cts:greekLit:tlg0012.tlg001:": {
            "urn": "urn:cts:greekLit:tlg0012.tlg001:",
            "groupUrn": "urn:cts:greekLit:tlg0012:",
            "node_kind": "work",
            "lang": "grc",
            "title": [{"lang": "eng", "value": "Iliad"}],
            "versions": [
                {
                    "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:",
                    "node_kind": "version",
                    "version_kind": "edition",
                    "lang": "grc",
                    "first_passage_urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7",
                    "citation_scheme": ["book", "line"],
                    "label": [{"lang": "eng", "value": "Iliad, Homeri Opera"}],
                    "description": [
                        {
                            "lang": "eng",
                            "value": "Homer, creator; Monro, D. B. (David Binning), 1836-1905, creator; Monro, D. B. (David Binning), 1836-1905, editor; Allen, Thomas W. (Thomas William), b. 1862, editor",
                        }
                    ],
                }
            ],
        },
        "urn:cts:greekLit:tlg0012.tlg002:": {
            "urn": "urn:cts:greekLit:tlg0012.tlg002:",
            "groupUrn": "urn:cts:greekLit:tlg0012:",
            "node_kind": "work",
            "lang": "grc",
            "label": [{"lang": "eng", "value": "Odyssey"}],
            "versions": [
                {
                    "urn": "urn:cts:greekLit:tlg0012.tlg002.perseus-grc2:",
                    "node_kind": "version",
                    "version_kind": "edition",
                    "lang": "grc",
                    "first_passage_urn": "urn:cts:greekLit:tlg0012.tlg002.perseus-grc2:1.1-1.10",
                    "citation_scheme": ["book", "line"],
                    "label": [
                        {"lang": "eng", "value": "Odyssey, Loeb classical library"}
                    ],
                    "description": [
                        {
                            "lang": "eng",
                            "value": "Homer, creator; Murray, A. T. (Augustus Taber), 1866-1940, editor",
                        }
                    ],
                }
            ],
        },
    },
    "versions": {
        "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:": {
            "path": "data/library/tlg0012/tlg001/tlg0012.tlg001.perseus-grc2.txt",
            "urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:",
            "node_kind": "version",
            "version_kind": "edition",
            "lang": "grc",
            "first_passage_urn": "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7",
            "citation_scheme": ["book", "line"],
            "label": [{"lang": "eng", "value": "Iliad, Homeri Opera"}],
            "description": [
                {
                    "lang": "eng",
                    "value": "Homer, creator; Monro, D. B. (David Binning), 1836-1905, creator; Monro, D. B. (David Binning), 1836-1905, editor; Allen, Thomas W. (Thomas William), b. 1862, editor",
                }
            ],
        },
        "urn:cts:greekLit:tlg0012.tlg002.perseus-grc2:": {
            "path": "data/library/tlg0012/tlg002/tlg0012.tlg002.perseus-grc2.txt",
            "urn": "urn:cts:greekLit:tlg0012.tlg002.perseus-grc2:",
            "node_kind": "version",
            "version_kind": "edition",
            "lang": "grc",
            "first_passage_urn": "urn:cts:greekLit:tlg0012.tlg002.perseus-grc2:1.1-1.10",
            "citation_scheme": ["book", "line"],
            "label": [{"lang": "eng", "value": "Odyssey, Loeb classical library"}],
            "description": [
                {
                    "lang": "eng",
                    "value": "Homer, creator; Murray, A. T. (Augustus Taber), 1866-1940, editor",
                }
            ],
        },
    },
}
