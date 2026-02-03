#!/bin/bash
set -e

# Pre-build script to prepare all function directories for deployment
# Copies core package and shared files (.ignore, build.sh) to each function
# Automatically discovers function directories by finding __main__.py files
# Usage: ./prepare-functions.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Dynamically find all function directories (those with __main__.py)
# Exclude virtualenv and other build artifacts
FUNCTION_DIRS=()
while IFS= read -r -d '' file; do
    dir=$(dirname "$file")
    FUNCTION_DIRS+=("$dir")
done < <(find functions/packages -name "__main__.py" -type f \
    -not -path "*/virtualenv/*" \
    -not -path "*/__pycache__/*" \
    -not -path "*/build/*" \
    -print0 | sort -z)

echo "Preparing ${#FUNCTION_DIRS[@]} function directories for build..."

for dir in "${FUNCTION_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Warning: Directory $dir does not exist, skipping..."
        continue
    fi
    cp -R core "$dir/"
    cp functions/.ignore "$dir/.ignore"
    cp functions/build.sh "$dir/build.sh"
done
