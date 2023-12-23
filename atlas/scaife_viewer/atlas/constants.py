# https://www.homermultitext.org/hmt-doc/cite/cts-urn-overview.html
# https://cite-architecture.github.io/ctsurn_spec/

# Reserved code points.
# All code points < Unicode x0020
# % Unicode x0025
# / Unicode x002F
# ? Unicode x003F
# # Unicode x0023
# : Unicode x003A
# . Unicode x002E
# @ Unicode x0040
# - Unicode x002D
# [ Unicode x005B
# ] Unicode x005D
# \ Unicode x005C
# " Unicode x0022
# & Unicode x0026
# < Unicode x003C
# > Unicode x003E
# ^ Unicode x005E
# ` Unicode x0060
# | Unicode x007C
# { Unicode x007B
# } Unicode x007D
# ~ Unicode x007E
import re


# fmt: off
RESERVED = "\\u0000-\\u0020" + "".join(
    "\\u{:04x}".format(ord(x)) for x in [
        "%",
        "/",
        "?",
        "#",
        ":",
        ".",
        "@",
        "-",
        "[",
        "]",
        '"',
        "\\",
        "&",
        "<",
        ">",
        "^",
        "`",
        "|",
        "{",
        "}",
        "~",
        # "@", # TODO: probably?
    ]
)
# fmt: on

NID = "urn"
CTS_NSS = "cts"
CITE_NSS = "cite"
NS = r"(?!urn)[a-z0-9-]{1,31}"
NODE = rf"[^{RESERVED}]"
WORK = rf"{NODE}\.{NODE}\.{NODE}(\.{NODE})?"
INCLUSIVE_RANGE = rf"{NODE}\-{NODE}"
SUBRANGE = rf"{NODE}\.{NODE}\-{NODE}\.{NODE}"
RANGE = rf"({INCLUSIVE_RANGE}|{SUBRANGE})"
INDEX = r"(\[\d+\])?"
SUBREF = rf"(@{NODE}{INDEX})?"
PASSAGE = rf"(((?:{NODE}\.)+)?{NODE}{SUBREF}|((?:{NODE}\.)+)?{RANGE}{SUBREF})"

CTS_URN_NODES = ["nid", "namespace", "textgroup", "work", "version", "exemplar"]
# TODO: Handle depth for `exemplar` by also taking `rank` into account
CTS_URN_DEPTHS = {key: idx for idx, key in enumerate(CTS_URN_NODES, 1)}
CTS_URN_RE = re.compile(rf"^{NID}:{CTS_NSS}:{NS}:{WORK}:{PASSAGE}$")

CITE_URN = None

NAMED_ENTITY_KIND_PERSON = "person"
NAMED_ENTITY_KIND_PLACE = "place"
NAMED_ENTITY_KINDS = [
    (NAMED_ENTITY_KIND_PERSON, "Person"),
    (NAMED_ENTITY_KIND_PLACE, "Place"),
]

HUMAN_FRIENDLY_LANGUAGE_MAP = {
    "eng": "English",
    "ang": "English, Old (ca.450-1100)",
    "fa": "Farsi",
    "far": "Farsi",
    "fre": "French",
    "ger": "German",
    "grc": "Greek",
    "heb": "Hebrew",
    "lat": "Latin",
}

TEXT_ANNOTATION_KIND_SCHOLIA = "scholia"
TEXT_ANNOTATION_KIND_SYNTAX_TREE = "syntax-tree"
TEXT_ANNOTATION_KIND_CHOICES = (
    (TEXT_ANNOTATION_KIND_SCHOLIA, "Scholia"),
    (TEXT_ANNOTATION_KIND_SYNTAX_TREE, "Syntax tree"),
)
