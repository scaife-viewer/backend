#!/usr/bin/env bash
set -eu

docker run --rm -it \
    -v $1:/opt/cts-utils/data \
    cts-utils:latest \
    bash -c "python tests/conversion.py /opt/cts-utils/data/cts-templates && \
    python tests/copy_files.py /opt/cts-utils/data/cts-templates"
