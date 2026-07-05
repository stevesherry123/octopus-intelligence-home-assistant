#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
destination="${project_root}/octopus_intelligence/app"

rm -rf "${destination}"
mkdir -p "${destination}"
cp "${project_root}/pyproject.toml" "${project_root}/README.md" "${destination}/"
cp -R "${project_root}/src" "${destination}/src"

echo "Synced Python source into ${destination}"

