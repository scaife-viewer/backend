#!/bin/bash
isort -rc scaife_viewer
black scaife_viewer
flake8 scaife_viewer
