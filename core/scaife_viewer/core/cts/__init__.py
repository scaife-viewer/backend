from MyCapytain.errors import UnknownCollection

from ..conf import settings

from .capitains import default_resolver  # noqa
from .collections import (  # noqa
    Collection,
    Text,
    TextGroup,
    TextInventory,
    Work,
    resolve_collection,
)
from .exceptions import (  # noqa
    CollectionDoesNotExist,
    InvalidPassageReference,
    InvalidURN,
    PassageDoesNotExist,
)
from .heal import heal
from .passage import Passage
from .reference import URN


def text_inventory() -> TextInventory:
    return TextInventory.load()


def collection(urn: str) -> Collection:
    try:
        metadata = TextInventory.load().metadata[urn]
    except UnknownCollection:
        raise CollectionDoesNotExist(f"{urn} does not exist")
    return resolve_collection(metadata.TYPE_URI)(URN(urn), metadata)


def _passage_urn_objs(urn: str):
    try:
        urn = URN(urn)
    except IndexError:
        raise InvalidURN(f"{urn} is invalid")
    if urn.reference is None:
        raise InvalidPassageReference("URN must contain a reference")

    reference = urn.reference
    if not settings.SCAIFE_VIEWER_CORE_NORMALIZE_SUBREFERENCES and (
        reference.start.subreference or (reference.end and reference.end.subreference)
    ):
        raise InvalidPassageReference(
            "URN must not contain a start or end subreference"
        )

    urn = urn.upTo(URN.NO_PASSAGE)
    c = collection(urn)
    if isinstance(c, Work):
        work = c
        text = next((text for text in work.texts() if text.kind == "edition"), None)
        if text is None:
            raise ValueError(f"{urn} does not have an edition")
    elif isinstance(c, Text):
        text = c
    else:
        raise ValueError(f"{urn} must reference a work or text")
    return text, reference


def passage(urn: str) -> Passage:
    text, reference = _passage_urn_objs(urn)
    passage = Passage(text, reference)
    if not passage.exists():
        raise PassageDoesNotExist(text, f"{reference} does not exist in {urn}")
    return passage


def passage_heal(urn: str) -> Passage:
    text, reference = _passage_urn_objs(urn)
    start, start_healed = heal(Passage(text, reference.start))
    if reference.end:
        end, end_healed = heal(Passage(text, reference.end))
        healed = any([start_healed, end_healed])
        if start == end:
            return start, healed
        return Passage(text, f"{start.reference}-{end.reference}"), healed
    else:
        return start, start_healed
