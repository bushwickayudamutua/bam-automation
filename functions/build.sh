#!/bin/bash
set -e

# Create fresh virtualenv
virtualenv virtualenv
source virtualenv/bin/activate

# Upgrade pip using python -m pip for reliability
python -m pip install --upgrade pip

# Install bam-core with dependencies to target directory
pip install --target ./virtualenv/lib/python3.11/site-packages ../../../lib/bam_core-0.0.1-py3-none-any.whl

# Reinstall binary packages for Linux platform (this overwrites the macOS versions)
pip install --platform manylinux2014_x86_64 --only-binary=:all: --target ./virtualenv/lib/python3.11/site-packages --upgrade --force-reinstall --no-deps \
    cryptography pyopenssl

echo "Build complete for Linux x86_64"
