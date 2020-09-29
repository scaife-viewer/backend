from unittest import mock

import pytest
from scaife_viewer.atlas.urn import URN


def test_urn_no_passage():
    urn = "urn:cts:0:0.0.0:"
    assert URN(urn).to_no_passage == urn


def test_urn_invalid():
    urn = "not:a.urn:"
    with pytest.raises(ValueError) as excinfo:
        URN(urn)
    assert str(excinfo.value) == f"Invalid URN: {urn}"


def test_urn_invalid_label():
    urn = "urn:cts:0:0.0.0:1.1"
    key = 12345
    with pytest.raises(KeyError) as excinfo:
        URN(urn).up_to(key)
    # Strange bug with this test case:
    # assert not excinfo.value.args[0] == str(excinfo.value)
    # str(excinfo.value) -> "'Provided key is not recognized: 12346'"
    # Value is wrapped in double quotes... ?! Use alternate method for now.
    assert excinfo.value.args[0] == f"Provided key is not recognized: {key}"


def test_urn_invalid_component():
    urn = "urn:cts:0:0.0.0:1.1"
    key = 5
    with pytest.raises(ValueError) as excinfo:
        URN(urn).up_to(key)
    assert str(excinfo.value) == "URN has no component: exemplar"


@pytest.mark.django_db
def test_urn_node_exception():
    urn = URN("urn:cts:0:0.0.0:1-2")
    with pytest.raises(NotImplementedError) as excinfo:
        urn.node
    assert str(excinfo.value) == "A range URN implies multiple nodes."


@mock.patch("scaife_viewer.atlas.models.Node.objects.get")
@pytest.mark.django_db
def test_urn_node_cached(mock_get):
    urn = URN("urn:cts:0:0.0.0:")
    assert mock_get.mock_calls == []
    urn.node
    assert mock_get.mock_calls == [mock.call(urn="urn:cts:0:0.0.0:")]
    urn.node
    assert len(mock_get.mock_calls) == 1
