from django.conf.urls import include, url


urlpatterns = [
    url(r"^", include("scaife_viewer.core.urls")),
]
