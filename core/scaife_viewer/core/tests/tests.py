from django.test import TestCase, override_settings
from django.urls import reverse

from ..utils import normalize_urn


class URNTests(TestCase):
    def test_urn_normalized(self):
        provided_urn = "urn:cts:greekLit:tlg0096.tlg002.First1K-grc1:"
        acceptable_urn = "urn:cts:greekLit:tlg0096.tlg002.First1K-grc1"
        result = normalize_urn(provided_urn)
        assert result == acceptable_urn

    @override_settings(SCAIFE_VIEWER_CORE_ALLOW_TRAILING_COLON=True)
    def test_urn_trailing_colon_not_normalized(self):
        provided_urn = "urn:cts:greekLit:tlg0096.tlg002.First1K-grc1:"
        result = normalize_urn(provided_urn)
        assert result == provided_urn

    def test_urn_unmodified(self):
        provided_urn = "urn:cts:greekLit:tlg0096.tlg002.First1K-grc1"
        result = normalize_urn(provided_urn)
        assert result == provided_urn


class ViewTests(TestCase):
    def test_reader_version_urn_redirects_to_first_passage(self):
        urn = "urn:cts:greekLit:tlg0096.tlg002.First1K-grc1"
        reader_url = reverse("reader", kwargs={"urn": urn})
        response = self.client.get(reader_url, follow=True)
        assert len(response.redirect_chain) == 2
        assert (
            response.wsgi_request.path
            == "/reader/urn:cts:greekLit:tlg0096.tlg002.First1K-grc1:1-4b/"
        )

    def test_reader_work_urn_redirects_to_library(self):
        urn = "urn:cts:greekLit:tlg0096.tlg002"
        reader_url = reverse("reader", kwargs={"urn": urn})
        response = self.client.get(reader_url, follow=True)
        assert len(response.redirect_chain) == 2
        assert response.wsgi_request.path == "/library/urn:cts:greekLit:tlg0096.tlg002/"
