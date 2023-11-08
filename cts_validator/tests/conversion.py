import sys
from pathlib import Path
from lxml import etree
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
    workdir = source.parent
    work_metadata = workdir / "__cts__.xml"
    parsed_work_metadata = etree.parse(work_metadata.open())
    return parsed_work_metadata.xpath("//ti:work/@urn", namespaces=XPATH_NAMESPACES)[0]


def get_version_types(source):
    parsed = etree.parse(source.open())
    cloned = etree.ElementTree(parsed.getroot())
    target = cloned.find('//tei:div[@type="integrated"]', namespaces=XPATH_NAMESPACES)
    # NOTE: This is done to maintain order in case we need to populate the CTS Work metadata
    # could be refactored using OrderedSet
    element_types = {}
    seen = set()
    for element_type in target.xpath(
        "//tei:div[@type]/@type", namespaces=XPATH_NAMESPACES
    ):
        if element_type in seen:
            continue
        if element_type in ALLOWED_VERSION_TYPES:
            element_types[element_type] = None
        seen.add(element_type)
    return list(element_types)


def generate_content(cloned, target, target_version, version_data):
    target_text = etree.Element("text")
    target_body = etree.Element("body")

    target_version.attrib.update(version_data["attrib"])
    etree.cleanup_namespaces(target_version)
    target_body.append(target_version)
    target_text.append(target_body)
    target.getparent().replace(target, target_text)
    version_data["content"] = etree.tostring(
        cloned, pretty_print=True, encoding="unicode"
    )


def process_version(source, work_urn, version_type):
    parsed = etree.parse(source.open())
    cloned = etree.ElementTree(parsed.getroot())
    target = cloned.find('//tei:div[@type="integrated"]', namespaces=XPATH_NAMESPACES)
    version_div = etree.Element("div", nsmap=XPATH_NAMESPACES)
    # FIXME: This assumes that we have content at depth=2; needs to be more
    # robust
    top_level_textparts = target.xpath(
        './tei:div[@type="textpart"]', namespaces=XPATH_NAMESPACES
    )
    version_data = None
    for textpart in top_level_textparts:
        new_textpart = etree.Element(
            textpart.tag,
            attrib=textpart.attrib,
        )
        for child in textpart.iterchildren():
            # NOTE: This assumes that the child is a textpart
            new_child = etree.Element(child.tag, attrib=child.attrib)
            for gchild in child.iterchildren():
                if gchild.attrib["type"] != version_type:
                    # NOTE: Ensures we don't process the grandchild, (which
                    # is assumed to be a container element) unless it matches
                    # the version we are looking for
                    continue
                if not version_data:
                    version_stem = gchild.attrib["n"].split(":", maxsplit=1)[0]
                    content_stem = target.attrib["n"]
                    version_data = {
                        "attrib": {
                            "type": version_type,
                            "{http://www.w3.org/XML/1998/namespace}lang": gchild.attrib[
                                "{http://www.w3.org/XML/1998/namespace}lang"
                            ],
                            "n": f"{work_urn}.{content_stem}-{version_stem}",
                        },
                    }
                for ggchild in gchild.iterchildren():
                    new_child.append(ggchild)
            new_textpart.append(new_child)
        version_div.append(new_textpart)

    # Insert our version_div into the template document and serialize
    # the XML to a string
    generate_content(cloned, target, version_div, version_data)
    return version_data


def main(path):
    """
    Usage: python conversion.py <path>
    """
    source = Path(path)
    work_urn = get_work_urn(source)
    version_types = get_version_types(source)

    version_lookup = {}
    for version_type in version_types:
        version_lookup[version_type] = process_version(source, work_urn, version_type)

    # FIXME: Copy files from source
    # FIXME: Improve path generation
    parent_path = source.parent.as_posix().replace("cts-templates", "data")
    outpath = Path(parent_path)
    proc = PySaxonProcessor(license=False)
    for version_data in version_lookup.values():
        name = version_data["attrib"]["n"].rsplit(":", maxsplit=1)[1]
        file_path = outpath / f"{name}.xml"
        parsed = proc.parse_xml(xml_text=version_data["content"])
        str_xml = proc.get_string_value(parsed)
        file_path.write_text("\n".join([XML_DECLARATION, str_xml]))


if __name__ == "__main__":
    path = None
    if not sys.argv[1:]:
        raise ValueError("Missing a filepath.")
    path = sys.argv[1]
    main(path)
