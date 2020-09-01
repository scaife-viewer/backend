from django.conf import settings  # noqa

from appconf import AppConf


class CoreAppConf(AppConf):
    ALLOW_TRAILING_COLON = False

    class Meta:
        prefix = "scaife_viewer_core"
