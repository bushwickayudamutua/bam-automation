#!/bin/bash
set -e

# Clean previous builds
rm -rf virtualenv
find core -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find core -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Create fresh virtualenv
virtualenv --without-pip virtualenv
source virtualenv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install bam-core with dependencies to target directory
pip install --target ./virtualenv/lib/python3.11/site-packages ./core

# Reinstall binary packages for Linux platform (this overwrites the macOS versions)
pip install --platform manylinux2014_x86_64 --only-binary=:all: --target ./virtualenv/lib/python3.11/site-packages --upgrade --force-reinstall --no-deps \
    pydantic pydantic-core email-validator charset-normalizer cryptography cffi

echo "Build complete for Linux x86_64"
