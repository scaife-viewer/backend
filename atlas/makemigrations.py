#!/usr/bin/env python
import os
import sys

import django

def run(*args):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scaife_viewer.atlas.tests.settings")
    django.setup()

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    django.core.management.call_command(
        "makemigrations",
        "scaife_viewer_atlas",
        *args
    )


if __name__ == "__main__":
    run(*sys.argv[1:])
