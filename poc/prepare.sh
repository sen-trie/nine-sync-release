#!/bin/sh
# usage: prepare.sh <path-to-installed-mmd_tools>
# Copies one mmd_tools (the POC used 4.5.5 from extensions.blender.org) into both the
# bundled and standalone slots. These copies are git-ignored.
HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$HERE/ext/ninesync_poc/third_party/mmd_tools" "$HERE/ext_standalone"
mkdir -p "$HERE/ext_standalone"
cp -r "$1" "$HERE/ext/ninesync_poc/third_party/mmd_tools"
cp -r "$1" "$HERE/ext_standalone/mmd_tools"
find "$HERE" -name __pycache__ -type d -prune -exec rm -rf {} +
