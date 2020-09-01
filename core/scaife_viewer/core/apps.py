from django.apps import AppConfig as BaseAppConfig
from django.utils.translation import ugettext_lazy as _


class AppConfig(BaseAppConfig):

    name = "scaife_viewer.core"
    label = "scaife_viewer_core"
    verbose_name = _("Scaife Viewer core")
