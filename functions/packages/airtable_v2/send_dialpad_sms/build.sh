#!/bin/bash

set -e

rm -rf virtualenv || true
mkdir -p virtualenv
virtualenv --without-pip virtualenv
# core/ gets added in the deploy process.
pip install ./core/ --target virtualenv/lib/python3.9/site-packages
