# PKG110 编译包

目标：PKG110 / OP5D2BL1 / pineapple / Qualcomm SM8650。
目标内核：`6.1.141-android14-11-o-g41d58e50fc53`。

## Docker 编译

1. Linux 主机安装 Docker，并确认当前用户可运行 `docker version`。
2. 在本目录执行：

```sh
python3 verify_kit.py
python3 -m pip install -r requirements.txt
QILIN_JOBS=2 bash build.sh
```

`build.sh` 会拉取 `ghcr.io/ylarod/ddk:android14-6.1`，检查 clang `r487747c`，准备 DDK 的 `modpost`，使用目标配置和 `Module.symvers` 编译 `cpuinfo_spoof.ko`，修复 `.modinfo` vermagic，并生成 `dist/build_report.json` 与 `dist/SHA256SUMS.txt`。

## 手工编译

如果你已有准备好的 Android 14 / Linux 6.1 内核输出目录：

```sh
python3 verify_kit.py
make KDIR=/absolute/path/to/prepared/android14-6.1-output LLVM=1 LLVM_IAS=1
python3 fix_vermagic.py cpuinfo_spoof.ko
python3 report.py cpuinfo_spoof.ko build_report.json
```

`KDIR` 必须包含 `.config`、`Module.symvers`、`CONFIG_MODVERSIONS=y`、`CONFIG_CFI_CLANG=y`、`CONFIG_COMPAT=y` 和 `CONFIG_SHADOW_CALL_STACK=y`。

## 编译完成后

将 `cpuinfo_spoof.ko`、`build_report.json` 和 `SHA256SUMS.txt` 保留在 `dist/`，先审阅 CRC、KCFI、vermagic、BTF 布局和目标 release，再把 KO 放入 KernelSU/Magisk 模块根目录。

目标配置 SHA256：`46108facbb8eee9c4e721243cf8687ffb97d7dcde49aae08cf49071baeebb661`。
vmlinux BTF SHA256：`3e689a4312d2fea4a7a053ccf1d0d48bd6922f84e3006ba11e073d47a8e42422`。
作者：杏仁 / xingren。
