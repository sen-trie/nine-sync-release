#!/bin/sh
# usage: [STD_VARIANT=ext445|ext4310|legacy445] run_gui.sh <scenario>
# Windowed Blender, isolated profile, own process. Never touches the user's profile.
B="${BLENDER:-blender}"
HERE="$(cd "$(dirname "$0")" && pwd)"
V="${STD_VARIANT:-ext445}"
if [ -n "$POC_PROFILE" ]; then P="$POC_PROFILE"; else P="$HERE/.profiles/gui_$1_${V}_$(date +%H%M%S)"; fi; echo "profile: $P"
FRESH=""; [ -d "$P/extensions" ] || FRESH=1
mkdir -p "$P/extensions/user_default" "$P/tmp"
[ -n "$FRESH" ] && cp -r "$HERE/ext/ninesync_poc" "$P/extensions/user_default/ninesync_poc"
STD="bl_ext.user_default.mmd_tools"
[ -n "$FRESH" ] && case "$V" in
  ext445) cp -r "$HERE/ext_standalone/mmd_tools" "$P/extensions/user_default/mmd_tools" ;;
  ext4310) cp -r "$HERE/ext_standalone_v4310/mmd_tools" "$P/extensions/user_default/mmd_tools" ;;
  legacy445) mkdir -p "$P/scripts/addons" && cp -r "$HERE/legacy/mmd_tools" "$P/scripts/addons/mmd_tools"; STD="mmd_tools" ;;
esac
export BLENDER_USER_RESOURCES="$(cygpath -w "$P")" POC_SCENARIO="$1" POC_STD="$STD" POC_OUT="$(cygpath -w "$P/result.json")" POC_TMP="$(cygpath -w "$P/tmp")"
FS="--factory-startup"; [ -n "$POC_KEEP_PREFS" ] && FS=""
"$B" $FS --python "$(cygpath -w "$HERE/gui_driver.py")" > "$P/stdout.txt" 2> "$P/stderr.txt"
echo "exit code: $?"
grep '^R|' "$P/stdout.txt" | tail -n 1
