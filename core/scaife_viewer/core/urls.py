from django.urls import path

from .views import LibraryCollectionView, Reader, library_text_redirect


urlpatterns = [
    path(
        "library/<str:urn>/",
        LibraryCollectionView.as_view(format="html"),
        name="library_collection",
    ),
    path(
        "library/<str:urn>/redirect/",
        library_text_redirect,
        name="library_text_redirect",
    ),
    path("reader/<str:urn>/", Reader.as_view(), name="reader"),
]
