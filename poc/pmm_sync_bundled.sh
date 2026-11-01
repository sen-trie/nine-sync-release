#!/bin/sh
# usage: pmm_sync_bundled.sh <file.pmm>   (read-only use of the PMM; throwaway profile)
B="${BLENDER:-blender}"
HERE="$(cd "$(dirname "$0")" && pwd)"
P="$HERE/.profiles/pmm_$(date +%H%M%S)"; mkdir -p "$P" "$HERE/dist"
export BLENDER_USER_RESOURCES="$(cygpath -w "$P")"
CORE="$HERE/../nine-sync-core"
"$B" -b --factory-startup --command extension build --source-dir "$(cygpath -w "$CORE")" --output-dir "$(cygpath -w "$HERE/dist")" >/dev/null 2>&1
ZIP="$(ls -t "$HERE"/dist/ninesync-*.zip | head -1)"
"$B" -b --factory-startup --command extension install-file -r user_default --enable "$(cygpath -w "$HERE/dist/ninesync_poc-0.0.1.zip")" >/dev/null 2>&1
"$B" -b --factory-startup --command extension install-file -r user_default "$(cygpath -w "$ZIP")" 2>&1 | grep STATUS
NINESYNC_CORE_SRC="$(cygpath -m "$CORE")" "$B" -b --factory-startup --python "$(cygpath -w "$HERE/pmm_sync_bundled.py")" -- "$1" 2>&1 | grep -E "PMMSYNC|^ok|^FAIL|Traceback|Error|enabled:" | cut -c1-220
