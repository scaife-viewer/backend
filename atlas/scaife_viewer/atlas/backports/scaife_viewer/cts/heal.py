# @@@ restore typing

from .passage import Passage
from .utils import natural_keys


def heal(passage):
    if not passage.exists():
        # @@@ always operates on the start of the passage
        ref_list = passage.reference.rsplit(":", maxsplit=1)[1].split("-")[0].split(".")
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
