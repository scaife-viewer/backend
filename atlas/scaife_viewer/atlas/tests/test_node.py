from collections import OrderedDict

import pytest
from scaife_viewer.atlas.models import Node
from scaife_viewer.atlas.tests import constants


@pytest.mark.django_db
def test_node_dump_tree_bypass_camel():
    Node.load_bulk(constants.TREE_DATA)

    assert Node.dump_tree(root=Node.objects.first(), to_camel=False) == [
        {
            "data": OrderedDict(
                [
                    ("idx", None),
                    ("kind", "node"),
                    ("urn", "urn:1:"),
                    ("ref", None),
                    ("rank", None),
                    ("text_content", None),
                    ("metadata", {}),
                ]
            ),
            "children": [
                {
                    "data": OrderedDict(
                        [
                            ("idx", None),
                            ("kind", "node"),
                            ("urn", "urn:11:"),
                            ("ref", None),
                            ("rank", None),
                            ("text_content", None),
                            ("metadata", {}),
                        ]
                    ),
                    "children": [
                        {
                            "data": OrderedDict(
                                [
                                    ("idx", None),
                                    ("kind", "node"),
                                    ("urn", "urn:111:"),
                                    ("ref", None),
                                    ("rank", None),
                                    ("text_content", None),
                                    ("metadata", {}),
                                ]
                            ),
                            "children": [
                                {
                                    "data": OrderedDict(
                                        [
                                            ("idx", None),
                                            ("kind", "node"),
                                            ("urn", "urn:1111:"),
                                            ("ref", None),
                                            ("rank", 1),
                                            ("text_content", None),
                                            ("metadata", {}),
                                        ]
                                    )
                                }
                            ],
                        },
                        {
                            "data": OrderedDict(
                                [
                                    ("idx", None),
                                    ("kind", "node"),
                                    ("urn", "urn:112:"),
                                    ("ref", None),
                                    ("rank", None),
                                    ("text_content", None),
                                    ("metadata", {}),
                                ]
                            ),
                            "children": [
                                {
                                    "data": OrderedDict(
                                        [
                                            ("idx", None),
                                            ("kind", "node"),
                                            ("urn", "urn:1121:"),
                                            ("ref", None),
                                            ("rank", 1),
                                            ("text_content", None),
                                            ("metadata", {}),
                                        ]
                                    )
                                }
                            ],
                        },
                    ],
                },
                {
                    "data": OrderedDict(
                        [
                            ("idx", None),
                            ("kind", "node"),
                            ("urn", "urn:12:"),
                            ("ref", None),
                            ("rank", None),
                            ("text_content", None),
                            ("metadata", {}),
                        ]
                    ),
                    "children": [
                        {
                            "data": OrderedDict(
                                [
                                    ("idx", None),
                                    ("kind", "node"),
                                    ("urn", "urn:121:"),
                                    ("ref", None),
                                    ("rank", None),
                                    ("text_content", None),
                                    ("metadata", {}),
                                ]
                            ),
                            "children": [
                                {
                                    "data": OrderedDict(
                                        [
                                            ("idx", None),
                                            ("kind", "node"),
                                            ("urn", "urn:1211:"),
                                            ("ref", None),
                                            ("rank", 1),
                                            ("text_content", None),
                                            ("metadata", {}),
                                        ]
                                    )
                                }
                            ],
                        }
                    ],
                },
            ],
        }
    ]


@pytest.mark.django_db
def test_node_dump_subtree():
    Node.load_bulk(constants.TREE_DATA)

    assert Node.dump_tree(root=Node.objects.get(urn="urn:11:")) == [
        {
            "data": {
                "idx": None,
                "kind": "node",
                "urn": "urn:11:",
                "ref": None,
                "rank": None,
                "textContent": None,
                "metadata": {},
            },
            "children": [
                {
                    "data": {
                        "idx": None,
                        "kind": "node",
                        "urn": "urn:111:",
                        "ref": None,
                        "rank": None,
                        "textContent": None,
                        "metadata": {},
                    },
                    "children": [
                        {
                            "data": {
                                "idx": None,
                                "kind": "node",
                                "urn": "urn:1111:",
                                "ref": None,
                                "rank": 1,
                                "textContent": None,
                                "metadata": {},
                            }
                        }
                    ],
                },
                {
                    "data": {
                        "idx": None,
                        "kind": "node",
                        "urn": "urn:112:",
                        "ref": None,
                        "rank": None,
                        "textContent": None,
                        "metadata": {},
                    },
                    "children": [
                        {
                            "data": {
                                "idx": None,
                                "kind": "node",
                                "urn": "urn:1121:",
                                "ref": None,
                                "rank": 1,
                                "textContent": None,
                                "metadata": {},
                            }
                        }
                    ],
                },
            ],
        }
    ]


@pytest.mark.django_db
def test_node_dump_tree_up_to():
    Node.load_bulk(constants.TREE_DATA)

    assert Node.dump_tree(root=Node.objects.first(), up_to="nid") == [
        {
            "data": {
                "idx": None,
                "kind": "node",
                "urn": "urn:1:",
                "ref": None,
                "rank": None,
                "textContent": None,
                "metadata": {},
            }
        }
    ]

    assert Node.dump_tree(root=Node.objects.first(), up_to="namespace") == [
        {
            "data": {
                "idx": None,
                "kind": "node",
                "urn": "urn:1:",
                "ref": None,
                "rank": None,
                "textContent": None,
                "metadata": {},
            },
            "children": [
                {
                    "data": {
                        "idx": None,
                        "kind": "node",
                        "urn": "urn:11:",
                        "ref": None,
                        "rank": None,
                        "textContent": None,
                        "metadata": {},
                    }
                },
                {
                    "data": {
                        "idx": None,
                        "kind": "node",
                        "urn": "urn:12:",
                        "ref": None,
                        "rank": None,
                        "textContent": None,
                        "metadata": {},
                    }
                },
            ],
        }
    ]

    assert Node.dump_tree(root=Node.objects.first(), up_to="textgroup") == [
        {
            "data": {
                "idx": None,
                "kind": "node",
                "urn": "urn:1:",
                "ref": None,
                "rank": None,
                "textContent": None,
                "metadata": {},
            },
            "children": [
                {
                    "data": {
                        "idx": None,
                        "kind": "node",
                        "urn": "urn:11:",
                        "ref": None,
                        "rank": None,
                        "textContent": None,
                        "metadata": {},
                    },
                    "children": [
                        {
                            "data": {
                                "idx": None,
                                "kind": "node",
                                "urn": "urn:111:",
                                "ref": None,
                                "rank": None,
                                "textContent": None,
                                "metadata": {},
                            }
                        },
                        {
                            "data": {
                                "idx": None,
                                "kind": "node",
                                "urn": "urn:112:",
                                "ref": None,
                                "rank": None,
                                "textContent": None,
                                "metadata": {},
                            }
                        },
                    ],
                },
                {
                    "data": {
                        "idx": None,
                        "kind": "node",
                        "urn": "urn:12:",
                        "ref": None,
                        "rank": None,
                        "textContent": None,
                        "metadata": {},
                    },
                    "children": [
                        {
                            "data": {
                                "idx": None,
                                "kind": "node",
                                "urn": "urn:121:",
                                "ref": None,
                                "rank": None,
                                "textContent": None,
                                "metadata": {},
                            }
                        }
                    ],
                },
            ],
        }
    ]

    assert Node.dump_tree(root=Node.objects.first(), up_to="work") == [
        {
            "data": {
                "idx": None,
                "kind": "node",
                "urn": "urn:1:",
                "ref": None,
                "rank": None,
                "textContent": None,
                "metadata": {},
            },
            "children": [
                {
                    "data": {
                        "idx": None,
                        "kind": "node",
                        "urn": "urn:11:",
                        "ref": None,
                        "rank": None,
                        "textContent": None,
                        "metadata": {},
                    },
                    "children": [
                        {
                            "data": {
                                "idx": None,
                                "kind": "node",
                                "urn": "urn:111:",
                                "ref": None,
                                "rank": None,
                                "textContent": None,
                                "metadata": {},
                            },
                            "children": [
                                {
                                    "data": {
                                        "idx": None,
                                        "kind": "node",
                                        "urn": "urn:1111:",
                                        "ref": None,
                                        "rank": 1,
                                        "textContent": None,
                                        "metadata": {},
                                    }
                                }
                            ],
                        },
                        {
                            "data": {
                                "idx": None,
                                "kind": "node",
                                "urn": "urn:112:",
                                "ref": None,
                                "rank": None,
                                "textContent": None,
                                "metadata": {},
                            },
                            "children": [
                                {
                                    "data": {
                                        "idx": None,
                                        "kind": "node",
                                        "urn": "urn:1121:",
                                        "ref": None,
                                        "rank": 1,
                                        "textContent": None,
                                        "metadata": {},
                                    }
                                }
                            ],
                        },
                    ],
                },
                {
                    "data": {
                        "idx": None,
                        "kind": "node",
                        "urn": "urn:12:",
                        "ref": None,
                        "rank": None,
                        "textContent": None,
                        "metadata": {},
                    },
                    "children": [
                        {
                            "data": {
                                "idx": None,
                                "kind": "node",
                                "urn": "urn:121:",
                                "ref": None,
                                "rank": None,
                                "textContent": None,
                                "metadata": {},
                            },
                            "children": [
                                {
                                    "data": {
                                        "idx": None,
                                        "kind": "node",
                                        "urn": "urn:1211:",
                                        "ref": None,
                                        "rank": 1,
                                        "textContent": None,
                                        "metadata": {},
                                    }
                                }
                            ],
                        }
                    ],
                },
            ],
        }
    ]
