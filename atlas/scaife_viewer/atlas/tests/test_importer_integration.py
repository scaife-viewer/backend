import copy
from unittest import mock

from treebeard.exceptions import PathOverflow

import pytest
from scaife_viewer.atlas.importers.versions import CTSImporter, Library
from scaife_viewer.atlas.models import Node
from scaife_viewer.atlas.tests import constants


library = Library(**constants.LIBRARY_DATA)


@pytest.mark.django_db
@mock.patch("scaife_viewer.atlas.importers.versions.CTSImporter.check_depth")
@mock.patch(
    "scaife_viewer.atlas.importers.versions.open",
    new_callable=mock.mock_open,
    read_data=constants.PASSAGE,
)
def test_importer_depth_exception(mock_open, mock_depth):
    mock_depth.return_value = True

    with pytest.raises(PathOverflow):
        CTSImporter(library, constants.VERSION_DATA, {}).apply()


@pytest.mark.django_db
@mock.patch(
    "scaife_viewer.atlas.importers.versions.open",
    new_callable=mock.mock_open,
    read_data=constants.PASSAGE,
)
def test_importer(mock_open):
    version_urn = "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:"

    CTSImporter(library, constants.VERSION_DATA, {}).apply()

    assert Node.objects.filter(kind="nid").count() == 1
    assert Node.objects.filter(kind="textgroup").count() == 1
    assert Node.objects.filter(kind="work").count() == 1
    assert Node.objects.filter(kind="version").count() == 1

    version = Node.objects.get(urn=version_urn)
    assert version.numchild == version.get_children().count()

    books = Node.objects.filter(kind="book")
    assert books.count() == 1
    assert all(book.rank == 1 for book in books)
    book = books.first()
    assert book.numchild == book.get_children().count()

    lines = Node.objects.filter(kind="line")
    assert lines.count() == 7
    assert all(line.rank == 2 for line in lines)
    assert all(line.kind == "line" for line in lines)
    assert all(line.idx == idx for idx, line in enumerate(lines))
    assert all(line.ref == f"{1}.{idx}" for idx, line in enumerate(lines, 1))
    assert all(
        line.urn == f"{version_urn}{1}.{idx}" for idx, line in enumerate(lines, 1)
    )


@pytest.mark.django_db
@mock.patch(
    "scaife_viewer.atlas.importers.versions.open",
    new_callable=mock.mock_open,
    read_data=constants.PASSAGE,
)
def test_importer_with_exemplar(mock_open):
    version_urn = "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:"
    exemplar_urn = "urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.card:"
    library_ = copy.deepcopy(library)
    exemplar_data = library_.versions.pop(version_urn)
    exemplar_data.update({"urn": exemplar_urn})
    library_.versions[exemplar_urn] = exemplar_data

    CTSImporter(library_, exemplar_data, {}).apply()

    assert Node.objects.filter(kind="nid").count() == 1
    assert Node.objects.filter(kind="textgroup").count() == 1
    assert Node.objects.filter(kind="work").count() == 1
    assert Node.objects.filter(kind="version").count() == 1
    assert Node.objects.filter(kind="exemplar").count() == 1

    books = Node.objects.filter(kind="book")
    assert books.count() == 1
    assert all(book.rank == 1 for book in books)

    lines = Node.objects.filter(kind="line")
    assert lines.count() == 7
    assert all(line.rank == 2 for line in lines)
    assert all(line.kind == "line" for line in lines)
    assert all(line.idx == idx for idx, line in enumerate(lines))
    assert all(line.ref == f"{1}.{idx}" for idx, line in enumerate(lines, 1))
    assert all(
        line.urn == f"{exemplar_urn}{1}.{idx}" for idx, line in enumerate(lines, 1)
    )
