from django.conf import settings  # noqa

from appconf import AppConf


class ATLASAppConf(AppConf):
    # `INGESTION_CONCURRENCY` defaults to number of processors
    # as reported by multiprocessing.cpu_count()
    INGESTION_CONCURRENCY = None

    class Meta:
        prefix = "scaife_viewer_atlas"
