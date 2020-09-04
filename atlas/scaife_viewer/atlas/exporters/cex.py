from cite_tools.cex_writer import (
    generate_catalog_block,
    generate_cex_metadata,
    generate_cts_data_block,
)

from ..models import Node


def escape_cex_special_characters(text):
    if text.startswith("!"):
        text = text.replace("!", "&excl;")
    if text.count("#"):
        text = text.replace("#", "&num;")
    return text


def extract_version_urn(p):
    return f'{p.rsplit(":", maxsplit=1)[0]}:'


def build_exemplar_urn(version_urn):
    parts = version_urn.rsplit(":")
    work_part = parts.pop(-2)
    work_parts = work_part.split(".")
    work_parts.append("tokens")
    new_work_part = ".".join(work_parts)
    parts.insert(-1, new_work_part)
    return ":".join(parts)


def prepare_catalog_entries(versions, exemplar_label=""):
    entries = []
    for version in versions:
        exemplar_urn = build_exemplar_urn(version.urn)
        entries.append(
            {
                "urn": exemplar_urn,
                "citation_scheme": ", ".join(
                    version.metadata["citation_scheme"] + ["tokens"]
                ),
                "group_name": version.get_parent().get_parent().metadata["label"],
                "work_title": version.get_parent().metadata["label"],
                "version_label": version.metadata["label"],
                "exemplar_label": exemplar_label,
                "online": "true",
                # @@@ grc vs Greek
                "lang": version.metadata["lang"],
            }
        )
    return entries


def prepare_cts_data(work_part_text_part_pairs):
    citable_nodes = []
    for work_part_urn, text_parts in work_part_text_part_pairs:
        for text_part in text_parts:
            for token in text_part.tokens.all():
                citable_nodes.append(
                    {
                        "urn": f"{work_part_urn}{token.ve_ref}",
                        "text": escape_cex_special_characters(token.value),
                    }
                )
    return citable_nodes


def export_alignment_citelibrary(passages):
    """
    Exports passages of text for alignment in Ducat
    """
    exemplar_text_part_pairs = []
    version_urns = []
    for passage in passages:
        version_urn = extract_version_urn(passage)
        version_urns.append(version_urn)
        exemplar_urn = build_exemplar_urn(version_urn)
        passage_text_parts = Node.objects.filter(urn__startswith=passage).exclude(
            tokens=None
        )
        exemplar_text_part_pairs.append((exemplar_urn, list(passage_text_parts)))

    versions = Node.objects.filter(urn__in=version_urns)
    catalog_entries = prepare_catalog_entries(versions, exemplar_label="tokens")
    nodes = prepare_cts_data(exemplar_text_part_pairs)
    return "\n".join(
        [
            generate_cex_metadata(),
            generate_catalog_block(catalog_entries),
            generate_cts_data_block(nodes),
        ]
    )


def main():
    passages = """urn:cts:farsiLit:hafez.divan.perseus-far1:1.1
urn:cts:farsiLit:hafez.divan.perseus-ger1:1.1
urn:cts:farsiLit:hafez.divan.perseus-eng1:1.1""".splitlines()
    print(export_alignment_citelibrary(passages))
