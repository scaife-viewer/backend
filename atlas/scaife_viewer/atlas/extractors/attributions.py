# -*- coding: utf-8 -*-
"""
Extract attribution data CTS-Compliant TEI XML
"""
import json
import logging
import os
import re
from collections import Counter, defaultdict

from scaife_viewer.atlas import constants
from scaife_viewer.atlas.conf import settings
from scaife_viewer.atlas.models import Node


logger = logging.getLogger(__name__)

ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "attributions"
)
STATS_DATA_PATH = os.path.join(settings.SV_ATLAS_DATA_DIR, "stats",)


def tei(name):
    return "{http://www.tei-c.org/ns/1.0}" + name


def ws(s):
    return re.sub(r"\s+", " ", s.strip())


def get_cts_resolver():
    # NOTE: This will perform poorly against the API resolver
    # FIXME: Decouple resolver from ATLAS
    from scaife_viewer.core.cts.capitains import default_resolver

    return default_resolver()


def get_tei_xml(resolver, urn):
    return resolver.getTextualNode(urn).xml


def extract_resp_statements(xml_obj):
    try:
        return list(iter(xml_obj.teiHeader.fileDesc.titleStmt.respStmt))
    except AttributeError as e:
        logger.debug(e)
        return None


def process_statements(lookup, urn, resp_statements):
    for child in resp_statements:

        persName = []
        resp = []
        orgName = []
        name = []
        for gchild in child.iterchildren():
            if gchild.tag == tei("persName"):
                if list(gchild.iterchildren()):
                    persName.append(ws(" ".join(gchild.xpath(".//text()"))))
                else:
                    persName.append(gchild.text.strip())
            elif gchild.tag == tei("resp"):
                assert not list(gchild.iterchildren())
                resp.append(ws(gchild.text))
            elif gchild.tag == tei("orgName"):
                assert not list(gchild.iterchildren())
                if gchild.text:
                    orgName.append(ws(gchild.text))
                else:
                    pass  # @@@
            elif gchild.tag == tei("name"):
                assert len(list(gchild.iterchildren())) == 0
                if gchild.text:
                    name.append(ws(gchild.text))
                else:
                    pass  # @@@
            else:
                logger.debug(gchild.tag)
                # quit()
        lookup[urn].append([persName, resp, orgName, name])
        logger.debug(persName)
        logger.debug(resp)
        logger.debug(orgName)
        logger.debug(name)


def build_attributions_lookup():
    resolver = get_cts_resolver()
    versions = Node.objects.filter(depth=constants.CTS_URN_DEPTHS["version"])

    # TODO: Expose proper edge-case support
    edgecases = {
        # https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/549552146ad00e60b065bd22e3935cdcdf529b4d/data/phi0914/phi001/phi0914.phi001.perseus-lat2.xml
        "urn:cts:latinLit:phi0914.phi001.perseus-lat2:",
    }

    lookup = defaultdict(list)
    for version in versions:
        urn = version.urn

        if urn in edgecases:
            continue

        safe_urn = urn[:-1]
        xml_obj = get_tei_xml(resolver, safe_urn)
        resp_statements = extract_resp_statements(xml_obj)
        if not resp_statements:
            continue

        process_statements(lookup, urn, resp_statements)
    return lookup


def prepare_attributions_annotation(lookup):
    attributions = []
    for urn, data in lookup.items():
        for row in data:
            # @@@ getlist type functionality for persons and organizations
            role = row[1]
            person = None
            organization = None
            orgs = [o.strip() for o in row[2] if o.strip]
            names = [n.strip() for n in row[0] + row[3] if n.strip]
            if not names and orgs:
                for org in orgs:
                    record = dict(
                        role=role[0],
                        person=None,
                        organization=dict(name=org),
                        data=dict(references=[urn]),
                    )
                    attributions.append(record)
                continue
            elif len(names) == len(row[2]):
                for name, org in zip(names, orgs):
                    record = dict(
                        role=role[0],
                        person=dict(name=name),
                        organization=dict(name=org),
                        data=dict(references=[urn]),
                    )
                    attributions.append(record)
            else:
                for org in orgs:
                    record = dict(
                        role=role[0],
                        person=None,
                        organization=dict(name=org),
                        data=dict(references=[urn]),
                    )
                    attributions.append(record)
                for name in names:
                    person = {
                        "name": name,
                    }
                    record = dict(
                        role=role[0],
                        person=person,
                        organization=organization,
                        data=dict(references=[urn]),
                    )
                    attributions.append(record)
    return attributions


def generate_attribution_stats(attributions):
    org_counter = Counter()
    person_counter = Counter()
    role_counter = Counter()
    urn_counter = Counter()
    for attribution in attributions:
        organization = attribution["organization"]
        if organization:
            org_counter[organization["name"]] += 1
        person = attribution["person"]
        if person:
            person_counter[person["name"]] += 1
        role_counter[attribution["role"]] += 1
        urn = attribution["data"]["references"][0]
        urn_counter[urn] += 1
    return dict(
        organizations=org_counter,
        people=person_counter,
        roles=role_counter,
        urns=urn_counter,
    )


def write_annotations(attributions):
    # TODO: Customize file_name
    os.makedirs(ANNOTATIONS_DATA_PATH, exist_ok=True)
    file_name = os.path.join(ANNOTATIONS_DATA_PATH, "corpora-attributions.json")
    with open(file_name, "w") as f:
        json.dump(attributions, f, ensure_ascii=False, indent=2)


def write_stats(stats):
    # TODO: Customize file_name
    os.makedirs(STATS_DATA_PATH, exist_ok=True)
    file_name = os.path.join(STATS_DATA_PATH, "attributions.json")

    with open(file_name, "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def extract_attributions():
    # TODO: filter by repo or URN
    # TODO: write lookup to temp dir
    lookup = build_attributions_lookup()

    attributions = prepare_attributions_annotation(lookup)
    write_annotations(attributions)

    stats = generate_attribution_stats(attributions)
    write_stats(stats)
