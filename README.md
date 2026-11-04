# PKG110 / OP5D2BL1 / SM8650 KernelSU 编译包

本目录是 Git/GitHub Actions 自编译源码包，不包含预编译 `cpuinfo_spoof.ko`。

## 目标画像

- 设备：PKG110 / OP5D2BL1
- 平台：pineapple
- SoC：Qualcomm SM8650
- Android：16 / SDK 36
- 内核：`6.1.141-android14-11-o-g41d58e50fc53`
- DDK：`android14-6.1`
- Docker：`ghcr.io/ylarod/ddk:android14-6.1`
- 作者：杏仁 / xingren

## GitHub Actions

把本目录解压后的全部内容直接放到 Git 仓库根目录，必须保留隐藏目录 `.github` 和文件 `.gitattributes`。不要把 ZIP 作为单个文件上传。

提交后打开：

`Actions → PKG110 SM8650 6.1 KO r1 → Run workflow`

新版本自检日志应包含：

```text
KIT_VERIFIED=pkg110-ddk-r1 files=17
SELF_CHECK=PASS shell_files=4 workflow=present target=PKG110
```

如果日志仍显示 `files=16`，运行的是旧提交；先提交包含 `self_check.py` 的最新根目录文件，再从该提交重新运行 workflow。

成功产物：

- `cpuinfo_spoof.ko`
- `build_report.json`
- `SHA256SUMS.txt`

## 本地 Linux/Docker 编译

```sh
python3 verify_kit.py
python3 self_check.py
python3 -m pip install -r requirements.txt
QILIN_JOBS=2 bash build.sh
```

也可以使用已经准备好的 Android 14 / Linux 6.1 内核输出目录：

```sh
make KDIR=/absolute/path/to/prepared/android14-6.1-output LLVM=1 LLVM_IAS=1
python3 fix_vermagic.py cpuinfo_spoof.ko
python3 report.py cpuinfo_spoof.ko build_report.json
```

`KDIR` 必须提供 `.config`、`Module.symvers`，并启用 `CONFIG_MODVERSIONS=y`、`CONFIG_CFI_CLANG=y`、`CONFIG_COMPAT=y` 和 `CONFIG_SHADOW_CALL_STACK=y`。

## 产物与验证

编译后先审阅 vermagic、CRC、KCFI、BTF 布局和目标 release，再将生成的 KO 放入 KernelSU/Magisk 模块目录。vermagic 匹配本身不等于完整 ABI/KMI 兼容；目标 CRC、KCFI、配置、BTF 和实际加载日志需要分别核对。

目标配置 SHA256：`46108facbb8eee9c4e721243cf8687ffb97d7dcde49aae08cf49071baeebb661`。

目标 vmlinux BTF SHA256：`3e689a4312d2fea4a7a053ccf1d0d48bd6922f84e3006ba11e073d47a8e42422`。
