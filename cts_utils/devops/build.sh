#!/usr/bin/env bash
set -eu

docker build -t cts-utils:latest -f devops/Dockerfile .
