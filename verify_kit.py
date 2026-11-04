#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
R=("cpuinfo_spoof.c","target_layout.h","kirin9020.h","Makefile","build.sh","prepare_ddk.sh","restore_modpost.awk","ddk","fix_vermagic.py","report.py","run.sh","verify_kit.py","requirements.txt","TARGET_PROFILE.json","TARGET_BTF.json","TARGET_CONFIG.txt","self_check.py")
def verify(root):
 p=json.loads((root/"TARGET_PROFILE.json").read_text(encoding='utf-8')); assert p["device_model"]=="PKG110" and p["ddk_target"]=="android14-6.1"
 for n in R: assert (root/n).is_file(),n
 assert hashlib.sha256((root/"TARGET_CONFIG.txt").read_bytes()).hexdigest()==p["config_sha256"]
 assert json.loads((root/"TARGET_BTF.json").read_text(encoding='utf-8'))["sha256"]==p["btf_sha256"]
 print("KIT_VERIFIED=pkg110-ddk-r1 files="+str(len(R)))
if __name__=="__main__": verify(Path(__file__).resolve().parent)
