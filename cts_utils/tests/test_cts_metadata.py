import os
import re
from pathlib import Path

import pytest
from lxml import etree
from lxml.etree import XPathEvalError, XPathSyntaxError


try:
    PDL_REFWORK_ROOT = Path(os.environ["PDL_REFWORK_ROOT"])
except KeyError:
    raise EnvironmentError("No PDL_REFWORK_ROOT environment variable has been set")


URN_RESERVED_CHARACTERS = ["%", "/", "?", "#"]
URN_EXCLUDED_CODE_POINTS = ["\\", '"', "&", "<", ">", "^", "`", "|", "{", "}", "~"]
CTS_URN_RESERVED_CHARACTERS = [":", ".", "@", "-", "[", "]"]


# FIXME: Set this to `False` to validate _all_ refsDecl patterns
TOP_LEVEL_ONLY = bool(int(os.environ.get("TOP_LEVEL_ONLY", "1")))

CODEPOINTS_PATTERN = (
    "["
    + "".join(
        re.escape(char)
        for char in URN_RESERVED_CHARACTERS
        + URN_EXCLUDED_CODE_POINTS
        + CTS_URN_RESERVED_CHARACTERS
    )
    + "]"
)
ALL_RESTRICTED_CODEPOINTS = re.compile(CODEPOINTS_PATTERN)


# backported from MyCapytain
CAPITANS_XPATH_NAMESPACES = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "ti": "http://chs.harvard.edu/xmlns/cts",
    "cpt": "http://purl.org/capitains/ns/1.0#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "xml": "http://www.w3.org/XML/1998/namespace",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
}
# backported from MyCapytain
CAPITANS_REFERENCE_REPLACER = re.compile(r"(@[a-zA-Z0-9:]+)(=)([\\$'\"?0-9]{3,6})")

VERSION_PATHS = sorted(
    list(f for f in PDL_REFWORK_ROOT.glob("data/**/*.xml") if f.name != "__cts__.xml")
)


# VERSION_PATHS = [
#     Path(
#         "/Users/jwegner/Data/development/repos/PerseusDL/canonical-greekLit/data/tlg0003/tlg001/tlg0003.tlg001.perseus-grc2.xml"
#     ),
#     Path(
#         "/Users/jwegner/Data/development/repos/PerseusDL/canonical-greekLit/data/tlg0012/tlg001/tlg0012.tlg001.perseus-grc2.xml"
#     ),
# ]

VERSION_PATH_IDS = [p.name for p in VERSION_PATHS]


# backported from MyCapytain
def _capitans_ref_replacer(match, passage):
    """Helper to replace xpath/scope/refsDecl on iteration with passage value

    :param match: A RegExp match
    :type match: re.SRE_MATCH
    :param passage: A list with subreference informations
    :type passage: iter

    :rtype: basestring
    :return: Replaced string
    """
    groups = match.groups()
    ref = next(passage)
    if ref is None:
        return groups[0]
    else:
        return "{1}='{0}'".format(ref, groups[0])


def extract_refs_decl_elem(parsed):
    refs_decls = parsed.xpath(
        "//tei:refsDecl[@n='CTS']", namespaces=CAPITANS_XPATH_NAMESPACES
    )
    try:
        refs_decl = refs_decls[0]
    except IndexError:
        pytest.fail("No refsDecl element found")
    return refs_decl


def valid_xpath(xpath_string):
    try:
        etree.XPath(xpath_string)
    except XPathSyntaxError:
        msg = f"{xpath_string} is not a valid XPath"
        raise XPathSyntaxError(msg)
    return xpath_string


def extract_xpath(cref_pattern, passage=None):
    cref_xpath_temp = cref_pattern.attrib["replacementPattern"][7:-1]
    if passage is None:
        return valid_xpath(CAPITANS_REFERENCE_REPLACER.sub(r"\1", cref_xpath_temp))
    passage = iter(passage)
    return valid_xpath(
        CAPITANS_REFERENCE_REPLACER.sub(
            lambda m: _capitans_ref_replacer(m, passage), cref_xpath_temp
        )
    )


def check_matches(parsed, max_pos, lookup, pos, references, match):
    next_child_pos = pos + 1
    if next_child_pos in lookup:
        next_references = references + [None] * next_child_pos
        next_child_xpath = extract_xpath(lookup[next_child_pos], next_references)
        matches = parsed.xpath(next_child_xpath, namespaces=CAPITANS_XPATH_NAMESPACES)
        try:
            assert matches
        except AssertionError:
            # TODO: If we have `n` on the lookup, that might improve our output
            trailer = f'[reference="{".".join(references)}" subtype="{match.attrib["subtype"]}" xpath="{next_child_xpath}"]'
            msg = f"Expected to find children, but none were found. {trailer}"
            pytest.fail(msg)

        for match in matches:
            check_matches(
                parsed,
                max_pos,
                lookup,
                next_child_pos,
                references + [match.attrib["n"]],
                match,
            )


@pytest.mark.parametrize("version_path", VERSION_PATHS, ids=VERSION_PATH_IDS)
def test_cts_metadata_files(version_path):
    """
    Run via:
    pip install pytest
    export PDL_REFWORK_ROOT=<path-to-pdl-refwork-repo>
    pytest test_cts_metadata.py
    """
    work_dir = version_path.parent
    work_metadata_file = work_dir / "__cts__.xml"
    assert (
        work_metadata_file.exists()
    ), f'No work metadata file found [path="{work_metadata_file}"]'

    version_stem = version_path.stem
    assert (
        version_stem in work_metadata_file.read_text()
    ), f'Version URN stem was not found in work metadata file [stem="{version_stem}" path="{work_metadata_file}"]'

    textgroup_dir = work_dir.parent
    textgroup_metadata_file = textgroup_dir / "__cts__.xml"
    assert (
        textgroup_metadata_file.exists()
    ), f'No work metadata file found [path="{textgroup_metadata_file}"]'


# TODO: Revisit dependency marks
# https://pytest-dependency.readthedocs.io/en/stable/usage.html
# @pytest.mark.dependency(name="test_has_refs_decl_element")
@pytest.mark.parametrize("version_path", VERSION_PATHS, ids=VERSION_PATH_IDS)
def test_has_refs_decl_element(version_path):
    """
    Test that a single refsDecl element is declared
    """
    parsed = etree.parse(version_path.open())
    refs_decls = parsed.xpath(
        "//tei:refsDecl[@n='CTS']", namespaces=CAPITANS_XPATH_NAMESPACES
    )
    num_refs_decls = len(refs_decls)
    assert num_refs_decls == 1


# TODO: Revisit dependency marks
# https://pytest-dependency.readthedocs.io/en/stable/usage.html
# @pytest.mark.dependency(depends=["test_has_refs_decl_element"])
@pytest.mark.parametrize("version_path", VERSION_PATHS, ids=VERSION_PATH_IDS)
def test_refs_decl_replacement_patterns(version_path):
    """
    Test that replacement patterns are valid xpaths
    """
    parsed = etree.parse(version_path.open())
    refs_decl = extract_refs_decl_elem(parsed)

    for cref_pattern in refs_decl.xpath(
        "//tei:cRefPattern", namespaces=CAPITANS_XPATH_NAMESPACES
    ):
        extract_xpath(cref_pattern)


@pytest.mark.parametrize("version_path", VERSION_PATHS, ids=VERSION_PATH_IDS)
def test_references_are_valid(version_path):
    """
    Tests that `@n` attrs are valid via https://cite-architecture.github.io/ctsurn_spec/#character-set
    """
    parsed = etree.parse(version_path.open())

    refs_decl = extract_refs_decl_elem(parsed)

    cref_patterns = refs_decl.xpath(
        "//tei:cRefPattern", namespaces=CAPITANS_XPATH_NAMESPACES
    )

    top_down_patterns = list(reversed(cref_patterns))
    lookup = dict()
    for pos, pattern in enumerate(top_down_patterns):
        lookup[pos] = pattern
        if TOP_LEVEL_ONLY:
            break

    # resolve all ref patterns
    contains_restricted = dict()
    idx = 0
    for pos, pattern in lookup.items():
        idx += 1
        cref_xpath = extract_xpath(pattern)

        try:
            matches = parsed.xpath(cref_xpath, namespaces=CAPITANS_XPATH_NAMESPACES)
        except XPathEvalError:
            msg = f"Invalid xpath: {cref_xpath}"
            pytest.fail(msg)

        for match in matches:
            n_attrib = match.attrib["n"]
            assert n_attrib
            restricted = ALL_RESTRICTED_CODEPOINTS.findall(n_attrib)
            # NOTE: we could raise an assertion error here, but we continue
            # to allow for all invalid references to be detected for the version
            if restricted:
                # TODO: Build up actual references with ancestors if we can
                # `idx` ensures that we have unique keys
                key = (idx, n_attrib)
                contains_restricted[key] = dict(
                    restricted=restricted,
                    subtype=match.attrib["subtype"],
                    xpath=cref_xpath,
                )
    restricted_messages = []
    references = set()
    for (_, reference), data in contains_restricted.items():
        references.add(reference)
        trailer = f'[reference="{reference}" restricted="{"".join(set(data["restricted"]))}" subtype="{data["subtype"]}" xpath="{data["xpath"]}"]'
        msg = f"Textpart reference contains restricted characters. {trailer}"
        restricted_messages.append(msg)
    if restricted_messages:
        msg = f'References with restricted characters: [references="{", ".join(references)}"]'
        messages = [msg] + restricted_messages
        pytest.fail("\n".join(messages))


@pytest.mark.parametrize("version_path", VERSION_PATHS, ids=VERSION_PATH_IDS)
def test_ref_patterns_return_results(version_path):
    """
    Tests that the specified cRefPattern instances return results.
    """
    parsed = etree.parse(version_path.open())

    refs_decl = extract_refs_decl_elem(parsed)

    cref_patterns = refs_decl.xpath(
        "//tei:cRefPattern", namespaces=CAPITANS_XPATH_NAMESPACES
    )
    top_down_patterns = list(reversed(cref_patterns))
    lookup = dict()
    for pos, pattern in enumerate(top_down_patterns):
        lookup[pos] = pattern
        if TOP_LEVEL_ONLY:
            break

    # resolve all ref patterns
    for pos, pattern in lookup.items():
        cref_xpath = extract_xpath(pattern)

        try:
            matches = parsed.xpath(cref_xpath, namespaces=CAPITANS_XPATH_NAMESPACES)
        except XPathEvalError:
            msg = f"Invalid xpath: {cref_xpath}"
            pytest.fail(msg)

        if not matches:
            msg = f"{cref_xpath} does not return results"
            pytest.fail(msg)


@pytest.mark.parametrize("version_path", VERSION_PATHS, ids=VERSION_PATH_IDS)
def test_balanced_refsdecls(version_path):
    """
    Test that all text parts are uniform (no unbalanced refs decls)
    """
    parsed = etree.parse(version_path.open())

    refs_decl = extract_refs_decl_elem(parsed)

    cref_patterns = refs_decl.xpath(
        "//tei:cRefPattern", namespaces=CAPITANS_XPATH_NAMESPACES
    )
    top_down_patterns = list(reversed(cref_patterns))
    max_pos = len(top_down_patterns) - 1
    lookup = dict()
    for pos, pattern in enumerate(top_down_patterns):
        lookup[pos] = pattern
        if TOP_LEVEL_ONLY:
            break

    top_level_xpath = extract_xpath(lookup[0])
    top_level_matches = parsed.xpath(
        top_level_xpath, namespaces=CAPITANS_XPATH_NAMESPACES
    )
    assert top_level_matches, f'No top-level matches found [xpath="{top_level_xpath}"]'
    if not TOP_LEVEL_ONLY:
        for match in top_level_matches:
            references = [match.attrib["n"]]
            check_matches(
                parsed, max_pos, lookup, pos=0, references=references, match=match
            )


@pytest.mark.parametrize("version_path", VERSION_PATHS, ids=VERSION_PATH_IDS)
def test_has_expected_filename(version_path):
    """
    Test that the version filename can be decomposed into a textgroup,
    work, and version
    """
    parts = version_path.stem.split(".")
    try:
        textgroup, work, version = parts
    except ValueError:
        msg = f"Could not split path into textgroup, version, work: {parts}"
        pytest.fail(msg)
