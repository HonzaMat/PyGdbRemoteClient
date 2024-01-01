#!/bin/bash

PY=python3
MAKE_CHANGES=0

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

TARGET=${SCRIPT_DIR}/src
TARGET_TESTS=${SCRIPT_DIR}/tests

show_usage() { 
    echo "Check the code using isort, black, flake8 and mypy." 1>&2; 
    echo "Usage: $0 [-e] [-p interpreter]" 1>&2; 
    echo "  -e            : Reformat the code automatically." 1>&2; 
    echo "                  [default: check only]" 1>&2; 
    echo "  -p interpeter : Specify python interpreter to use." 1>&2;     
    echo "                  [default: python3]" 1>&2;     
    exit 1
}

while getopts "p:eh" opt; do
    case "${opt}" in
        e)
            MAKE_CHANGES=1
            ;;
        p)
            PY=${OPTARG}
            ;;            
        *)
            show_usage
            ;;
    esac
done

set -e

echo ""
echo "======================================================"
echo " Isort"
echo "======================================================"

if [ $MAKE_CHANGES -ne 0 ]; then
    ${PY} -m isort --profile black ${TARGET} ${TARGET_TESTS}
else
    ${PY} -m isort --profile black --check-only --diff ${TARGET} ${TARGET_TESTS}
fi

echo ""
echo "======================================================"
echo " Black"
echo "======================================================"

if [ $MAKE_CHANGES -ne 0 ]; then
    ${PY} -m black ${TARGET} ${TARGET_TESTS}
else
    ${PY} -m black --check --diff ${TARGET} ${TARGET_TESTS}
fi

echo ""
echo "======================================================"
echo " Flake8"
echo "======================================================"

${PY} -m flake8 --max-line-length 88 --extend-ignore E203 ${TARGET}

echo ""
echo "======================================================"
echo " Mypy"
echo "======================================================"

MYPYPATH=${TARGET} ${PY} -m mypy --strict --package gdb_remote_client
