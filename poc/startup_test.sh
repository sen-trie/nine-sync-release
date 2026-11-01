#!/bin/sh
# usage: startup_test.sh "<order>"   order = "std,poc" or "poc,std": enabled in that order,
# prefs saved in an isolated profile, then Blender is relaunched with those prefs.
HERE="$(cd "$(dirname "$0")" && pwd)"
TAG="$(echo "$1" | tr ',' '_')"
export POC_PROFILE="$HERE/.profiles/startup_${TAG}_$(date +%H%M%S)"
POC_ORDER="$1" POC_HANG=100 "$HERE/run_gui.sh" startup_prepare
POC_KEEP_PREFS=1 POC_HANG=150 "$HERE/run_gui.sh" startup_check
