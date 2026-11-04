#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
cd "$ROOT"
LOG="$ROOT/build_logs"
OUT="$ROOT/dist"
mkdir -p "$LOG"
exec >"$LOG/build.log" 2>&1
fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}
printf 'BUILD_KIT=pkg110-ddk-r1\n'
for tool in bash docker python3 sha256sum; do
  command -v "$tool" >/dev/null 2>&1 || fail "Missing tool: $tool"
done
python3 verify_kit.py
python3 -c 'from elftools.elf.elffile import ELFFile' || fail 'Install requirements.txt first'
[ ! -e "$OUT" ] || fail "Existing dist preserved: $OUT; use a new working copy"
docker version >/dev/null 2>&1
WRAPPER_HOME=$(mktemp -d "$LOG/ddk-home.XXXXXX")
mkdir -p "$WRAPPER_HOME/.ddk"
printf 'github\n' > "$WRAPPER_HOME/.ddk/source"
printf 'docker\n' > "$WRAPPER_HOME/.ddk/mode"
HOME="$WRAPPER_HOME" bash "$ROOT/ddk" pull --target android14-6.1
IMAGE=ghcr.io/ylarod/ddk:android14-6.1
IMAGE_ID=$(docker image inspect "$IMAGE" --format '{{.Id}}')
docker image inspect "$IMAGE_ID" > "$LOG/image-inspect.json"
docker run --platform linux/amd64 --rm -v "$ROOT:/build" -w /build "$IMAGE_ID" sh -c 'clang --version' > "$LOG/clang-version.txt"
cat "$LOG/clang-version.txt"
grep -q 'r487747c' "$LOG/clang-version.txt" || fail 'Target requires clang-r487747c'
docker run --platform linux/amd64 --rm -v "$ROOT:/build" -w /build "$IMAGE_ID" make clean
docker run --platform linux/amd64 --rm -v "$ROOT:/build" -w /build "$IMAGE_ID" make all LLVM=1 LLVM_IAS=1 -j"${QILIN_JOBS:-2}"
[ -s cpuinfo_spoof.ko ] || fail 'No module produced'
cp cpuinfo_spoof.ko "$LOG/cpuinfo_spoof.raw.ko"
if [ -s cpuinfo_spoof.mod.c ]; then
  cp cpuinfo_spoof.mod.c "$LOG/cpuinfo_spoof.mod.c"
  printf 'MODPOST_VERSION_TABLE_BEGIN\n'
  sed -n '/____versions/,/};/p' cpuinfo_spoof.mod.c
  printf 'MODPOST_VERSION_TABLE_END\n'
fi
STAGING=$(mktemp -d "$LOG/dist.XXXXXX")
cp cpuinfo_spoof.ko "$STAGING/cpuinfo_spoof.ko"
python3 fix_vermagic.py "$STAGING/cpuinfo_spoof.ko"
python3 report.py "$STAGING/cpuinfo_spoof.ko" "$STAGING/build_report.json"
cp run.sh TARGET_PROFILE.json TARGET_BTF.json TARGET_CONFIG.txt KIT_MANIFEST.json "$STAGING/"
cp "$LOG/image-inspect.json" "$STAGING/"
cd "$STAGING"
sha256sum cpuinfo_spoof.ko build_report.json run.sh TARGET_PROFILE.json TARGET_BTF.json TARGET_CONFIG.txt KIT_MANIFEST.json image-inspect.json > SHA256SUMS.txt
cd "$ROOT"
mv -- "$STAGING" "$OUT"
printf 'KO_BUILD_SUCCESS\nDIST=%s\n' "$OUT"
