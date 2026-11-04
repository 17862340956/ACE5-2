#!/bin/sh
# Restore stock 6.1 modpost export/CRC handling inside the disposable DDK.
set -eu
KIT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
KDIR=${1:?prepared kernel output path required}
KDIR=$(CDPATH= cd -- "$KDIR" && pwd -P)
SRC=''
for candidate in "$KDIR/source" /opt/ddk/src/android14-6.1; do
    if [ -f "$candidate/scripts/mod/modpost.c" ]; then
        SRC=$(CDPATH= cd -- "$candidate" && pwd -P)
        break
    fi
done
[ -n "$SRC" ] || { echo 'ERROR: DDK modpost source not found' >&2; exit 1; }
MODPOST="$SRC/scripts/mod/modpost.c"
# A prepared 6.1 output Makefile includes the source tree Makefile by path.
# Fail rather than patch an unrelated fallback tree.
if [ "$SRC" != "$KDIR" ]; then
    grep -Fq "$SRC/Makefile" "$KDIR/Makefile" || { echo 'ERROR: selected modpost source does not match prepared Kbuild Makefile' >&2; exit 1; }
fi
printf 'DDK_MODPOST_SOURCE=%s\n' "$MODPOST"
LOG="$KIT/build_logs"
mkdir -p "$LOG"
# Preserve the DDK source and the exact transformed source as diagnostics.
cp "$MODPOST" "$LOG/modpost-before.c"
awk -f "$KIT/restore_modpost.awk" "$MODPOST" > "$LOG/modpost-restored.c"
grep -Eq '^[[:space:]]*check_exports\(mod\);[[:space:]]*$' "$LOG/modpost-restored.c" || { echo 'ERROR: expected stock check_exports call not found' >&2; exit 1; }
grep -Eq '^[[:space:]]*s->module[[:space:]]*=[[:space:]]*exp->module;[[:space:]]*$' "$LOG/modpost-restored.c" || { echo 'ERROR: expected stock export-to-module assignment not found' >&2; exit 1; }
if ! cmp -s "$MODPOST" "$LOG/modpost-restored.c"; then
    cp "$LOG/modpost-restored.c" "$MODPOST"
    echo 'DDK_MODPOST_PATCH_RESTORED=1'
else
    echo 'DDK_MODPOST_PATCH_RESTORED=already-stock'
fi
# In Android 6.1, prepare0 explicitly descends into scripts/mod.
# The scripts target does not: scripts/Makefile lists mod in subdir- only for
# cleaning. prepare0 updates host modpost and required generated headers; it
# does not link vmlinux or build the kernel's full module set.
touch "$MODPOST"
make -C "$KDIR" LLVM=1 prepare0
[ -x "$KDIR/scripts/mod/modpost" ] || { echo 'ERROR: rebuilt host modpost missing' >&2; exit 1; }
if [ "$MODPOST" -nt "$KDIR/scripts/mod/modpost" ]; then
    echo 'ERROR: host modpost was not rebuilt from restored source' >&2
    exit 1
fi
sha256sum "$MODPOST" "$KDIR/scripts/mod/modpost" > "$LOG/modpost-restored.sha256"
echo 'DDK_MODPOST_CRC_RESOLUTION=restored'
