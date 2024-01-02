#!/bin/bash

# Helper script to upload a release (content of dist/) to PyPI

set -e

if [ "$1" == "--production" ]; then
    echo "Uploading to production PyPI" >&2
    PROD=1
elif [ "$1" == "--test" ]; then
    echo "Uploading to test-only PyPI" >&2
    PROD=0
else
    echo "Usage: $0 {--production | --test}" >&2
    exit 1
fi

python3 -m twine check dist/*

if [ $PROD -ne 0 ]; then
    python3 -m twine upload dist/*
else
    python3 -m twine upload --repository testpypi dist/*
fi