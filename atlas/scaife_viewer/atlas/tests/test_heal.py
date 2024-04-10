import pytest

from scaife_viewer.atlas.models import Node
from scaife_viewer.atlas.tests import constants
from scaife_viewer.atlas.backports.scaife_viewer.cts import passage_heal


@pytest.mark.django_db
def test_passage_not_healed():
    Node.load_bulk(constants.TREE_DATA)
    workish = Node.objects.last()
    workish.urn = "urn:cts:greekLit:tlg0012.tlg001:"
    workish.save()
    versionish = workish.add_child(
        urn="urn:cts:greekLit:tlg0012.tlg001:perseus-grc2:",
        kind="version",
    )
    child = versionish.add_child(
        urn=f"{versionish.urn}1", kind="textpart", rank=1, ref="1"
    )
    passage, healed = passage_heal(child.urn)
    assert healed is False
    assert passage.reference == child.urn


@pytest.mark.django_db
def test_passage_healed():
    Node.load_bulk(constants.TREE_DATA)
    workish = Node.objects.last()
    workish.urn = "urn:cts:greekLit:tlg0012.tlg001:"
    workish.save()
    versionish = workish.add_child(
        urn="urn:cts:greekLit:tlg0012.tlg001:perseus-grc2:",
        kind="version",
    )
    child = versionish.add_child(
        urn=f"{versionish.urn}1", kind="textpart", rank=1, ref="1"
    )
    passage, healed = passage_heal(f"{versionish.urn}1.1")
    assert healed is True
    assert passage.reference == child.urn


@pytest.mark.django_db
def test_passage_healed_alphanumeric():
    Node.load_bulk(constants.TREE_DATA)
    workish = Node.objects.last()
    workish.urn = "urn:cts:greekLit:tlg0012.tlg001:"
    workish.save()
    versionish = workish.add_child(
        urn="urn:cts:greekLit:tlg0012.tlg001:perseus-grc2:",
        kind="version",
    )
    versionish.add_child(urn=f"{versionish.urn}1", kind="textpart", rank=1, ref="1")
    child_d = versionish.add_child(
        urn=f"{versionish.urn}d", kind="textpart", rank=1, ref="d"
    )
    passage, healed = passage_heal(f"{versionish.urn}d.1")
    assert healed is True
    assert passage.reference == child_d.urn
