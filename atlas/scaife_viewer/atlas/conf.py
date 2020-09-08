import base64

from django.conf import settings  # noqa

from appconf import AppConf


class ATLASAppConf(AppConf):
    IN_MEMORY_PASSAGE_CHUNK_MAX = 2500
    NODE_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    DATA_MODEL_ID = base64.b64encode(b"2020-09-08-001\n").decode()

    # required settings
    # DATA_DIR

    class Meta:
        prefix = "sv_atlas"
        required = ["DATA_DIR"]
