#!/bin/bash

# SPDX-License-Identifier: MIT

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd "$SCRIPT_DIR"

PYTHONPATH=${SCRIPT_DIR}/src/ python3 -m pytest tests/ -vv