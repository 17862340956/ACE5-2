#!/system/bin/sh
# OPD2407 target entry: inspect by default, full activates the display preset.
umask 077
STAGE=${1:-inspect}
case "$STAGE" in inspect|uts|cpus|topology|cpufreq|cpuinfo|combo|full) ;; *) echo '用法：sh run.sh [inspect|uts|cpus|topology|cpufreq|cpuinfo|combo|full]'; exit 1 ;; esac
[ "$(id -u)" = 0 ] || { echo '请使用 ROOT 执行。'; exit 1; }
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P) || exit 1
BASE=/data/adb
[ -d "$BASE" ] && [ -w "$BASE" ] || BASE=/data/local/tmp
OUT="$BASE/opd2407_r1_$(date '+%Y%m%d_%H%M%S')_$$"
mkdir -p "$OUT" || exit 1
TARGET=6.1.128-android14-11-o-g024c24b34f5e
REV=qilin-opd2407-61-r1
CONFIG_SHA=78030136b5d95f3cec4444bf72f4141083c5eca315cb9eed7fb407968b89faee
BTF_SHA=9372cccd4e885660697069315eed8d1a25cb327a3959054f2c51febf8d8def67
say() { printf '%s\n' "$*"; printf '%s\n' "$*" >> "$OUT/run.txt"; }
finish() {
    dmesg > "$OUT/dmesg.txt" 2> "$OUT/dmesg.error"
    sync
    if tar -czf "$OUT.tar.gz" -C "$BASE" "${OUT##*/}" 2> "$OUT/archive.error"; then
        echo "日志包：$OUT.tar.gz"
    else echo "日志目录：$OUT"; fi
}
fail() { say "FAIL $*"; finish; exit 1; }
step() { printf '%s\n' "$*" > "$OUT/last_step.txt"; sync; }
value() { sed -n "s/^$1=//p" "$OUT/status.txt"; }
expect() { [ "$2" = "$3" ] || fail "$1=$2 expected=$3"; say "PASS $1=$2"; }
[ "$(getprop ro.product.model)" = OPD2407 ] || fail '型号不是OPD2407。'
[ "$(getprop ro.board.platform)" = mt6897 ] || fail '平台不是mt6897。'
[ "$(getconf PAGESIZE 2>/dev/null)" = 4096 ] || fail '页大小不是4096。'
for TOOL in sha256sum strings gzip awk sed grep insmod rmmod; do command -v "$TOOL" >/dev/null 2>&1 || fail "缺少工具：$TOOL"; done
KO="$DIR/cpuinfo_spoof.ko"
REPORT="$DIR/build_report.json"
[ -s "$KO" ] && [ -s "$REPORT" ] || fail '缺少配套KO或报告。'
[ "$(awk -F '"' '/"validation"/ {print $4; exit}' "$REPORT")" = passed ] || fail '构建报告未通过验证。'
expect revision "$(awk -F '"' '/"revision"/ {print $4; exit}' "$REPORT")" "$REV"
expect target_btf "$(awk -F '"' '/"target_btf_sha256"/ {print $4; exit}' "$REPORT")" "$BTF_SHA"
HASH=$(sha256sum "$KO" | awk '{print $1}')
expect module_sha256 "$HASH" "$(awk -F '"' '/"sha256"/ {print $4; exit}' "$REPORT")"
cp "$REPORT" "$OUT/build_report.json"
strings "$KO" > "$OUT/module_strings.txt"
grep -qx "version=$REV" "$OUT/module_strings.txt" || fail '模块版本不符。'
grep -q "^vermagic=$TARGET " "$OUT/module_strings.txt" || fail '模块release不符。'
step target_profile
gzip -dc /proc/config.gz > "$OUT/live.config" 2> "$OUT/config.error" || fail '读取内核配置失败。'
expect live_config "$(sha256sum "$OUT/live.config" | awk '{print $1}')" "$CONFIG_SHA"
[ -r /sys/kernel/btf/vmlinux ] || fail '读取目标BTF失败。'
expect live_btf "$(sha256sum /sys/kernel/btf/vmlinux | awk '{print $1}')" "$BTF_SHA"
RP=''
if [ "$STAGE" = full ]; then
    for TOOL in /data/adb/ksu/bin/resetprop /data/adb/magisk/resetprop; do
        [ ! -x "$TOOL" ] || { RP=$TOOL; break; }
    done
    [ -n "$RP" ] || RP=$(command -v resetprop 2>/dev/null)
    [ -n "$RP" ] && [ -x "$RP" ] || fail 'full模式缺少resetprop。'
fi
if [ -d /sys/module/cpuinfo_spoof ]; then
    cat /proc/cpuinfo_spoof > "$OUT/status.txt" 2> "$OUT/status.error" || fail '已有实例状态不可读。'
    expect resident_revision "$(value revision)" "$REV"
    expect resident_release "$(value original_release)" "$TARGET"
    if [ "$(value stage)" != "$STAGE" ]; then
        if [ "$(value stage)" = inspect ] && [ "$(value pinned)" = 0 ] && [ "$(value applied)" = 0 ]; then
            step unload_inspect
            rmmod cpuinfo_spoof > "$OUT/rmmod.txt" 2>&1 || fail '卸载只读检查实例失败。'
        else
            fail '已有修改实例驻留，重启后再切换模式。'
        fi
    fi
fi
if [ ! -d /sys/module/cpuinfo_spoof ]; then
    expect running_release "$(uname -r)" "$TARGET"
    POINTERS=0
    case "$STAGE" in cpus|topology|cpufreq|cpuinfo|combo|full) POINTERS=1 ;; esac
    step before_insmod
    insmod "$KO" stage="$STAGE" pointer_tests="$POINTERS" > "$OUT/insmod.txt" 2>&1
    RC=$?
    cat "$OUT/insmod.txt"
    [ "$RC" = 0 ] || fail "加载失败rc=$RC"
fi
step read_status
cat /proc/cpuinfo_spoof > "$OUT/status.txt" 2> "$OUT/status.error" || fail '状态节点读取失败。'
cat "$OUT/status.txt"
expect revision "$(value revision)" "$REV"
expect stage "$(value stage)" "$STAGE"
expect last_error "$(value last_error)" 0
if [ "$STAGE" = inspect ]; then
    expect state "$(value state)" inspect_only
    expect applied "$(value applied)" 0
    for KEY in preflight_uts preflight_cpus preflight_topology preflight_cpufreq preflight_cpuinfo; do
        expect "$KEY" "$(value "$KEY")" 0
    done
    say 'INSPECT_OK：未发布替换指针。需要启用预设时执行 sh run.sh full。'
else
    expect state "$(value state)" active
    expect planned_equals_applied "$(value applied)" "$(value planned)"
    if [ "$STAGE" = full ]; then
        expect pointer_applied "$(value pointer_applied)" 7
        expect applied "$(value applied)" 8
        expect uts_applied "$(value uts_applied)" 1
        cat /proc/cpuinfo > "$OUT/cpuinfo.txt" || fail '读取CPUINFO失败。'
        expect processor_lines "$(grep -c '^processor' "$OUT/cpuinfo.txt")" 12
        expect uname_release "$(uname -r)" 6.1.128-HUAWEI-Kirin9020
        for KEY in online possible present; do
            expect "$KEY" "$(cat /sys/devices/system/cpu/$KEY)" 0-11
        done
        for CPU in 0 1 2 3 4 5 6 7; do
            if [ "$CPU" -lt 4 ]; then CORE=$CPU; PACKAGE=0; else CORE=$((CPU-4)); PACKAGE=1; fi
            expect "cpu${CPU}_core" "$(cat /sys/devices/system/cpu/cpu$CPU/topology/core_id)" "$CORE"
            expect "cpu${CPU}_package" "$(cat /sys/devices/system/cpu/cpu$CPU/topology/physical_package_id)" "$PACKAGE"
        done
        FREQS='307200 441600 556800 672000 787200 902400 1017600 1113600 1228800 1344000 1459200 1555200 1670400 1785600 1900800 2016000 2188800 2323200 2457600 2592000 2707200 2803200 2918400 3000000 3187200'
        for POLICY in policy0 policy4 policy7; do
            expect "$POLICY" "$(cat /sys/devices/system/cpu/cpufreq/$POLICY/scaling_available_frequencies)" "$FREQS"
        done
        step properties
        "$RP" -n ro.soc.model Kirin9020 > "$OUT/resetprop.txt" 2>&1 || fail '修改soc型号属性失败。'
        "$RP" -n ro.soc.manufacturer HiSilicon >> "$OUT/resetprop.txt" 2>&1 || fail '修改soc厂商属性失败。'
        expect soc_model "$(getprop ro.soc.model)" Kirin9020
        expect soc_manufacturer "$(getprop ro.soc.manufacturer)" HiSilicon
    fi
fi
step complete
say "COMPLETE stage=$STAGE；文本预设不改变真实CPU数量、指令能力或硬件频率。"
finish
