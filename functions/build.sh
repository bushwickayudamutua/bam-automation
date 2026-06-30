#!/bin/bash
set -e

# Create fresh virtualenv
virtualenv virtualenv
source virtualenv/bin/activate

# Upgrade pip using python -m pip for reliability
python -m pip install --upgrade pip msal pyopenssl

# Install bam-core with dependencies to target directory
python -m pip install --target ./virtualenv/lib/python3.11/site-packages ../../../lib/core

echo "Build complete"
