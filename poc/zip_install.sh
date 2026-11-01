#!/bin/sh
# Builds the POC extension ZIP, validates it, installs it from the ZIP into a fresh
# isolated profile, enables it, uses it, and checks that nothing but __pycache__ was
# written inside the install directory. Background mode, own profile.
B="${BLENDER:-blender}"
HERE="$(cd "$(dirname "$0")" && pwd)"
P="$HERE/.profiles/zip_$(date +%H%M%S)"
mkdir -p "$P" "$HERE/dist"
export BLENDER_USER_RESOURCES="$(cygpath -w "$P")"
rm -f "$HERE/dist/ninesync_poc-0.0.1.zip"
"$B" -b --factory-startup --command extension validate "$HERE/ext/ninesync_poc" || exit 1
"$B" -b --factory-startup --command extension build --source-dir "$HERE/ext/ninesync_poc" --output-dir "$HERE/dist" || exit 1
sha256sum "$HERE/dist/ninesync_poc-0.0.1.zip"
"$B" -b --factory-startup --command extension install-file -r user_default --enable "$HERE/dist/ninesync_poc-0.0.1.zip" || exit 1
INSTALL="$P/extensions/user_default/ninesync_poc"
find "$INSTALL" -type f ! -path '*__pycache__*' -exec sha256sum {} + | sort -k2 > "$P/before.txt"
"$B" -b --factory-startup --python "$(cygpath -w "$HERE/zip_check.py")" 2>&1 | grep -E "^ZIP|Traceback|Error"
find "$INSTALL" -type f ! -path '*__pycache__*' -exec sha256sum {} + | sort -k2 > "$P/after.txt"
if diff -q "$P/before.txt" "$P/after.txt" >/dev/null; then echo "ZIP install dir unchanged apart from __pycache__"; else echo "ZIP FAIL: install dir changed"; diff "$P/before.txt" "$P/after.txt"; fi
"$B" -b --factory-startup --command extension remove ninesync_poc 2>&1 | tail -2
[ -d "$INSTALL" ] && echo "ZIP FAIL: install dir still present after remove" || echo "ZIP uninstall removed the directory"
