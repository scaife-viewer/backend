from .heal import heal
from .passage import Passage


# def _passage_urn_objs(urn: str):
#     # @@@ validation validation validation
#     try:
#         urn = URN(urn)
#     except IndexError:
#         raise InvalidURN(f"{urn} is invalid")
#     if urn.reference is None:
#         raise InvalidPassageReference("URN must contain a reference")
#     reference = urn.reference
#     if _has_subreference(reference.start) or (reference.end and _has_subreference(reference.end)):
#         raise InvalidPassageReference("URN must not contain a start or end subreference")
#     urn = urn.upTo(URN.NO_PASSAGE)
#     c = collection(urn)
#     if isinstance(c, Work):
#         work = c
#         text = next((text for text in work.texts() if text.kind == "edition"), None)
#         if text is None:
#             raise ValueError(f"{urn} does not have an edition")
#     elif isinstance(c, Text):
#         text = c
#     else:
#         raise ValueError(f"{urn} must reference a work or text")
#     return text, reference


def passage_heal(urn: str):
    # @@@ actually validate the passage
    # version, reference = _passage_urn_objs(urn)
    passage = Passage(urn)
    version = passage.version
    references = passage.reference.rsplit(":", maxsplit=1)[1].split("-")
    reference_start = references[0]
    reference_end = next(iter(references[1:]), None)
    start, start_healed = heal(Passage(f"{version.urn}{reference_start}"))
    if reference_end:
        end, end_healed = heal(Passage(f"{version.urn}{reference_end}"))
        healed = any([start_healed, end_healed])
        if start == end:
            return start, healed
        # @@@ optimize this a bit
        return Passage(f"{start.start.urn}-{end.start.ref}"), healed
    else:
        return start, start_healed
