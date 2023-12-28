import time
import logging
from django.core.management.base import BaseCommand

import elasticsearch
from ...conf import settings
from ...search import es


class Command(BaseCommand):

    help = "Creates a new ElasticSearch index"

    def handle(self, *args, **options):
        ts = int(time.time())
        index_name = f"{settings.ELASTICSEARCH_INDEX_NAME}-{ts}"
        es.indices.create(index=index_name, ignore=400)
        self.stdout.write(index_name)
