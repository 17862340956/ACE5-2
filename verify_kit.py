#!/usr/bin/env python3
"""Check all required repository inputs before reading target metadata."""
from pathlib import Path
import hashlib
import json
import sys

R = (
    "cpuinfo_spoof.c", "target_layout.h", "kirin9020.h", "Makefile",
    "build.sh", "prepare_ddk.sh", "restore_modpost.awk", "ddk",
    "fix_vermagic.py", "report.py", "run.sh", "verify_kit.py",
    "requirements.txt", "TARGET_PROFILE.json", "TARGET_BTF.json",
    "TARGET_CONFIG.txt", "self_check.py",
)


def fail(message):
    print("KIT_VERIFY_FAILED: " + message, file=sys.stderr)
    raise SystemExit(1)


def read_json(root, name):
    try:
        value = json.loads((root / name).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        fail(f"Invalid {name}: {exc}")
    if not isinstance(value, dict):
        fail(f"{name} must contain a JSON object")
    return value


def verify(root):
    root = Path(root).resolve()
    missing = [name for name in R if not (root / name).is_file()]
    if missing:
        print("CHECKOUT_ROOT=" + str(root), file=sys.stderr)
        for name in missing:
            print("MISSING_INPUT=" + name, file=sys.stderr)
        fail("Missing repository inputs. Extract ALL files from the full r3 source ZIP "
             "into the repository root, commit them, and start a NEW workflow run "
             "on that branch. File names are case-sensitive on Linux.")
    profile = read_json(root, "TARGET_PROFILE.json")
    if profile.get("device_model") != "PKG110" or profile.get("ddk_target") != "android14-6.1":
        fail("TARGET_PROFILE.json identity mismatch; expected PKG110 / android14-6.1")
    config_digest = hashlib.sha256((root / "TARGET_CONFIG.txt").read_bytes()).hexdigest()
    if config_digest != profile.get("config_sha256"):
        fail("TARGET_CONFIG.txt SHA256 mismatch")
    if read_json(root, "TARGET_BTF.json").get("sha256") != profile.get("btf_sha256"):
        fail("TARGET_BTF.json target SHA256 mismatch")
    print("KIT_VERIFIED=pkg110-ddk-r1 files=" + str(len(R)))


if __name__ == "__main__":
    verify(Path(__file__).resolve().parent)
