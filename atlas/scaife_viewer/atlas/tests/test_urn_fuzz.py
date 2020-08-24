import hypothesis

from scaife_viewer.atlas.tests.strategies import URNs
from scaife_viewer.atlas.urn import URN


@hypothesis.given(URNs.cts_urns())
def test_urn_absolute(urn):
    assert URN(urn).absolute == urn


@hypothesis.given(URNs.cts_urns().map(URN))
def test_urn_routes(urn):
    components = urn.absolute.split(":")
    work_components = components[3].split(".")

    assert urn.up_to(urn.NID) == f"{':'.join(components[:2])}:"
    assert urn.up_to(urn.NAMESPACE) == f"{':'.join(components[:3])}:"
    expected = f"{urn.up_to(urn.NAMESPACE)}{work_components[0]}:"
    assert urn.up_to(urn.TEXTGROUP) == expected
    expected = f"{urn.up_to(urn.NAMESPACE)}{'.'.join(work_components[:2])}:"
    assert urn.up_to(urn.WORK) == expected
    expected = f"{urn.up_to(urn.NAMESPACE)}{'.'.join(work_components[:3])}:"
    assert urn.up_to(urn.VERSION) == expected
    if urn.has_exemplar:
        expected = f"{urn.up_to(urn.NAMESPACE)}{'.'.join(work_components)}:"
        assert urn.up_to(urn.EXEMPLAR) == expected
    assert urn.up_to(urn.NO_PASSAGE) == f"{':'.join(components[:4])}:"
    assert urn.passage == components[-1]
