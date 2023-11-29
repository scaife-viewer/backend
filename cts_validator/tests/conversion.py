import io
import sys
from pathlib import Path
from lxml import etree, builder
from saxonche import PySaxonProcessor


XPATH_NAMESPACES = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "ti": "http://chs.harvard.edu/xmlns/cts",
    "cpt": "http://purl.org/capitains/ns/1.0#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "xml": "http://www.w3.org/XML/1998/namespace",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
}
TEI_NS = "{%s}" % XPATH_NAMESPACES["tei"]

ALLOWED_VERSION_TYPES = {
    "edition",
    "commentary",
    "translation",
}

XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'


def get_work_urn(source):
    parsed = etree.parse(source.open())
    return parsed.xpath('//tei:div[@type="work"]/@n', namespaces=XPATH_NAMESPACES)[0]


def get_version_types(source):
    parsed = etree.parse(source.open())
    cloned = etree.ElementTree(parsed.getroot())
    target = cloned.find('//tei:div[@type="work"]', namespaces=XPATH_NAMESPACES)
    # NOTE: This is done to maintain order in case we need to populate the CTS Work metadata
    # could be refactored using OrderedSet
    unique_versions = {}
    seen = set()
    for type_element in target.xpath(
        "//tei:div[@type]", namespaces=XPATH_NAMESPACES
    ):
        element_type = type_element.attrib["type"]
        # TODO: Add a smarter filter here?
        n_attr = type_element.get("n", "")
        if n_attr.count(":") and not n_attr.startswith("urn"):
            key = (element_type, n_attr.split(":", maxsplit=1)[0])
            if key in seen:
                continue
            if element_type in ALLOWED_VERSION_TYPES:
                unique_versions[key] = None
            seen.add(element_type)
    return list(unique_versions)


def safe_nsmap(nsmap):
    return {
        key: uri
        for key, uri in nsmap.items()
        if uri != "http://www.w3.org/2001/XInclude"
    }


# Backported from https://gitlab.com/brillpublishers/code/bpt-converter/-/blob/master/bptconverter/cts/tei.py
def render_cts_replacement_patterns(levels=[("work", "div")]):
    """
    Builds the CTS replacement patterns for references.

    Parameters
    ----------
    levels : list
        Levels is a list of tuples, each tuple consists of (name, xml_tag).
        Example: ('level1', 'div')

    Returns
    -------
    refsDecl : string
        The XML for the reference declaration
    """
    tei = builder.ElementMaker(namespace=XPATH_NAMESPACES["tei"])

    ref_pattern = "/tei:TEI/tei:text/tei:body/tei:div"
    ref_description = "This pointer pattern extracts "
    replacement_patterns = []

    for i, (name, tag) in enumerate(levels):
        ref_pattern += f"/tei:{tag}[@n='${i+1}']"
        ref_description += " and " if i > 0 else ""
        ref_description += name
        match_pattern = ".".join((i + 1) * ["(\\w+)"])
        replacement_patterns = [
            tei.cRefPattern(
                tei.p(ref_description),
                n=name,
                matchPattern=match_pattern,
                replacementPattern=f"#xpath({ref_pattern})",
            )
        ] + replacement_patterns

    replacement_patterns = tei.refsDecl(*replacement_patterns, n="CTS")

    return replacement_patterns


def rewrite_refsdecls(cloned, version_data):
    dynamic_refsdecl = cloned.find(
        '//tei:refsDecl[@type="dynamic"]', namespaces=XPATH_NAMESPACES
    )
    if dynamic_refsdecl is None:
        return
    refs_decl = render_cts_replacement_patterns(
        version_data["textpart_levels"].values()
    )
    dynamic_refsdecl.getparent().replace(dynamic_refsdecl, refs_decl)


def generate_content(cloned, target, target_version, version_data):
    target_text = etree.Element("text")
    target_body = etree.Element("body")

    target_version.attrib.update(version_data["attrib"])
    etree.cleanup_namespaces(target_version)
    target_body.append(target_version)
    target_text.append(target_body)
    target.getparent().replace(target, target_text)

    rewrite_refsdecls(cloned, version_data)

    # NOTE: Removes xi:include
    root = cloned.getroot()
    new_root = etree.Element(root.tag, nsmap=safe_nsmap(root.nsmap), attrib=root.attrib)
    for child in root:
        new_root.append(child)

    version_data["content"] = etree.tostring(
        new_root, pretty_print=True, encoding="unicode"
    )


def safe_attributes(attributes):
    safe_attributes = {}
    for k, v in attributes.items():
        if k in {"{http://www.w3.org/XML/1998/namespace}base"}:
            continue
        safe_attributes[k] = v
    return safe_attributes


def process_textpart(
    integrated, textpart, version_type, version_data, version_div, work_urn
):
    new_textpart = etree.Element(
        textpart.tag,
        attrib=safe_attributes(textpart.attrib),
    )
    for child in textpart.iterchildren():
        # NOTE: This assumes that the child is a textpart
        child_type = child.attrib.get("type")
        new_child = etree.Element(child.tag, attrib=safe_attributes(child.attrib))
        if child_type == "textpart":
            result, new_child_textpart = process_textpart(
                integrated, child, version_type, version_data, version_div, work_urn
            )
            version_data.update(result)
            new_textpart.append(new_child_textpart)
            new_child = None
            continue
        if child_type in ALLOWED_VERSION_TYPES and child_type != version_type:
            # NOTE: Ensures we don't process the grandchild, (which
            # is assumed to be a container element) unless it matches
            # the version we are looking for
            continue
        if child_type == version_type and not version_data:
            version_stem = child.attrib["n"].split(":", maxsplit=1)[0]
            content_stem = integrated.attrib["n"]
            version_data = {
                "attrib": {
                    "type": version_type,
                    "n": f"{work_urn}.{content_stem}-{version_stem}",
                    "{http://www.w3.org/XML/1998/namespace}lang": child.attrib[
                        "{http://www.w3.org/XML/1998/namespace}lang"
                    ],
                },
            }
            # continue
        for grandchild in child.iterchildren():
            grandchild_type = grandchild.attrib.get("type")
            if grandchild_type in ALLOWED_VERSION_TYPES:
                # NOTE: Ensures we don't process the grandchild, (which
                # is assumed to be a container element) unless it matches
                # the version we are looking for
                continue
            new_child.append(grandchild)
        if child_type in ALLOWED_VERSION_TYPES:
            for grandchild in new_child.iterchildren():
                new_textpart.append(grandchild)
        else:
            new_textpart.append(new_child)
    version_div.append(new_textpart)
    return version_data, new_textpart


def process_integrated_version(source, work_urn, version_type):
    parsed = etree.parse(source.open())
    parsed.xinclude()
    cloned = etree.ElementTree(parsed.getroot())
    target = cloned.find('//tei:div[@type="work"]', namespaces=XPATH_NAMESPACES)
    version_div = etree.Element("div", nsmap=XPATH_NAMESPACES)
    integrated = target.find('./tei:div[@type="integrated"]', namespaces=XPATH_NAMESPACES)
    top_level_textparts = integrated.xpath(
        './tei:div[@type="textpart"]', namespaces=XPATH_NAMESPACES
    )
    version_data = {}
    for textpart in top_level_textparts:
        version_data, _ = process_textpart(
            integrated, textpart, version_type, version_data, version_div, work_urn
        )

    version_data["textpart_levels"] = extract_textpart_levels(version_div)
    # Insert our version_div into the template document and serialize
    # the XML to a string
    generate_content(cloned, target, version_div, version_data)
    return version_data


def get_standalone_version_selectors(parsed):
    target = parsed.find('//tei:div[@type="work"]', namespaces=XPATH_NAMESPACES)
    children = target.xpath('./tei:div[@type="standalone"]/child::*', namespaces=XPATH_NAMESPACES)
    # NOTE: We're using getpath versus building up a selector
    # using the @n attrib
    for child in children:
        yield parsed.getpath(child)


def populate_textpart_level_lookup(lookup, element, depth=1):
    if element is None:
        return
    lookup[depth] = (
        element.attrib["subtype"],
        etree.QName(element).localname,
    )
    child = element.find('./tei:div[@type="textpart"]', namespaces=XPATH_NAMESPACES)
    if child is not None:
        return populate_textpart_level_lookup(lookup, child, depth=depth + 1)


def extract_textpart_levels(version_div):
    # NOTE: This assumes that there are always "balanced"
    # refsdecls; if there are not, we may miss cRefPattern
    # instances
    lookup = {}
    first_top_level_texpart = version_div.find(
        './tei:div[@type="textpart"]', namespaces=XPATH_NAMESPACES
    )
    populate_textpart_level_lookup(lookup, first_top_level_texpart)
    return lookup


def process_standalone_versions(source, work_urn):
    parsed = etree.parse(source.open())
    parsed.xinclude()
    # We keep a copy of the parsed XML in-memory to modify for each standalone version
    frozen_xml = io.BytesIO(etree.tostring(parsed))

    selectors = get_standalone_version_selectors(parsed)
    lookup = dict()
    for pos, selector in enumerate(selectors):
        cloned = etree.parse(frozen_xml)
        target = cloned.find('//tei:div[@type="work"]', namespaces=XPATH_NAMESPACES)
        # we re-fetch the element using the selector extracted above
        version_div = cloned.xpath(selector)[0]
        element_type = version_div.attrib["type"]
        version_data = dict(
            attrib=version_div.attrib,
            textpart_levels=extract_textpart_levels(version_div),
        )
        generate_content(cloned, target, version_div, version_data)
        key = (element_type, str(pos))
        lookup[key] = version_data
    return lookup


def process_work_template(source):
    work_urn = get_work_urn(source)
    version_types = get_version_types(source)

    version_lookup = {}
    for version_key in version_types:
        version_type, _ = version_key
        version_lookup[version_key] = process_integrated_version(source, work_urn, version_type)

    version_lookup.update(
        process_standalone_versions(source, work_urn)
    )
    # FIXME: Copy files from source
    parent_path = source.parent.as_posix().replace("cts-templates", "data")
    outpath = Path(parent_path)
    outpath.mkdir(exist_ok=True, parents=True)
    proc = PySaxonProcessor(license=False)
    for version_data in version_lookup.values():
        name = version_data["attrib"]["n"].rsplit(":", maxsplit=1)[1]
        file_path = outpath / f"{name}.xml"
        parsed = proc.parse_xml(xml_text=version_data["content"])
        str_xml = proc.get_string_value(parsed)
        file_path.write_text("\n".join([XML_DECLARATION, str_xml]))


def get_content_template_paths(path):
    return path.glob("*/*/content-*.xml")


def main(path):
    """
    Usage: python conversion.py <path>
    """
    for content_template_path in get_content_template_paths(path):
        process_work_template(content_template_path)


if __name__ == "__main__":
    path = None
    if not sys.argv[1:]:
        raise ValueError("Missing a filepath.")
    path = Path(sys.argv[1])
    main(path)
