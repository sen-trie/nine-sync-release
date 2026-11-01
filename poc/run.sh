#!/bin/sh
# usage: run.sh <scenario>
B="${BLENDER:-blender}"
HERE="$(cd "$(dirname "$0")" && pwd)"
P="$HERE/.profiles/$1"
rm -rf "$P" && mkdir -p "$P"
BLENDER_USER_RESOURCES="$(cygpath -w "$P")" "$B" -b --factory-startup --python "$(cygpath -w "$HERE/run_scenario.py")" -- "$1"
