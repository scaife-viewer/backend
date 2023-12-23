# @@@ restore typing
import re

from ....chunking_poc import venetus_a_ref_to_folio
from .passage import Passage
from .utils import natural_keys


VENETUS_A_FOLIOS_URN = "urn:cts:greekLit:tlg0012.tlg001.msA-folios:"
VENETUS_A_HEALABLE_REGEX = re.compile(r"[\d]+[vr].{0,1}")


def heal(passage):
    if not passage.exists():
        # @@@ always operates on the start of the passage
        passage_ref = passage.reference.rsplit(":", maxsplit=1)[1].split("-")[0]
        ref_list = passage_ref.split(".")

        if (
            passage.version.urn == VENETUS_A_FOLIOS_URN
            and not VENETUS_A_HEALABLE_REGEX.match(passage_ref)
        ):
            folio_urn = venetus_a_ref_to_folio(passage.version, passage_ref)
            if folio_urn:
                return Passage(f"{folio_urn}"), True

        healed_node = heal_recursive(passage.version, ref_list)
        return Passage(f"{healed_node.urn}"), True
    return passage, False


def heal_recursive(node, reference_list):
    first, *rest = reference_list
    healthy_node = heal_node(node, first)
    if rest:
        return heal_recursive(healthy_node, rest)
    else:
        return healthy_node


def heal_node(node, r):
    # @@@ in-memory vs using querysets
    children = list(node.get_children())
    if not children:
        return node
    prev_child = children[0]
    r = natural_keys(r)
    for child in children:
        lcp_natural = natural_keys(child.lowest_citable_part)
        if lcp_natural > r:
            break
        prev_child = child
    return prev_child
