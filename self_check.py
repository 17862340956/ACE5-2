#!/usr/bin/env python3
"""Static repository checks that run before the Docker build."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
SHELL_FILES = ("build.sh", "prepare_ddk.sh", "run.sh", "ddk")

def fail(message: str) -> None:
    raise SystemExit(f"SELF_CHECK_FAILED: {message}")

def main() -> None:
    for name in SHELL_FILES:
        path = ROOT / name
        if not path.is_file():
            fail(f"missing {name}")
        raw = path.read_bytes()
        if b"\r" in raw:
            fail(f"CRLF or carriage return found in {name}; convert the file to LF")
        if b"\x00" in raw:
            fail(f"NUL byte found in {name}")
        text = raw.decode("utf-8")
        if not text.endswith("\n"):
            fail(f"missing final LF in {name}")
        if name == "prepare_ddk.sh":
            if "for candidate in" not in text or "do\n" not in text or "\ndone\n" not in text:
                fail("prepare_ddk.sh loop is incomplete")
            if len(re.findall(r"(?m)^\s*if\b", text)) != len(re.findall(r"(?m)^\s*fi\b", text)):
                fail("prepare_ddk.sh if/fi count mismatch")
        if name == "build.sh":
            if text.count("if [ -s cpuinfo_spoof.mod.c ]; then") != 1:
                fail("build.sh modpost if block missing")
            if text.count("\nfi\n") != 1:
                fail("build.sh if/fi count mismatch")
            if "sha256sum cpuinfo_spoof.ko" not in text:
                fail("build.sh output hash step missing")
    workflow = ROOT / ".github" / "workflows" / "build.yml"
    if not workflow.is_file():
        fail("missing .github/workflows/build.yml")
    workflow_text = workflow.read_text(encoding="utf-8")
    required = ("python3 self_check.py", "bash -n build.sh", "sh -n prepare_ddk.sh")
    for item in required:
        if item not in workflow_text:
            fail(f"workflow missing: {item}")
    profile = json.loads((ROOT / "TARGET_PROFILE.json").read_text(encoding="utf-8"))
    if profile.get("device_model") != "PKG110" or profile.get("ddk_target") != "android14-6.1":
        fail("target profile identity mismatch")
    print("SELF_CHECK=PASS shell_files=4 workflow=present target=PKG110")

if __name__ == "__main__":
    main()
