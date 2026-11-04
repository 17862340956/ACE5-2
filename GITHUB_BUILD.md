# GitHub Actions 编译

作者：杏仁 / xingren。

1. 在 GitHub 创建仓库，把本包解压后的全部内容放到仓库根目录，包括隐藏目录 `.github` 和文件 `.gitattributes`。
2. 确认仓库中存在 `.github/workflows/build.yml`，以及根目录的 `build.sh`、`Makefile`、`cpuinfo_spoof.c`。
3. 打开仓库 **Actions → PKG110 SM8650 6.1 KO r1 → Run workflow**，选择分支后运行。工作流使用手动触发；请将工作流提交到默认分支。
4. 运行结束后，在页面底部 **Artifacts** 下载 `pkg110-ko-r1-运行编号`；若构建失败，当前工作流会直接打印 `build_logs/build.log`，同时可下载 `pkg110-diagnostics-r1-运行编号` 查看完整日志。
5. 新版日志应包含 `BUILD_KIT_REVISION=build-kdir-fix-r4`、`CHECKOUT_ROOT=present`、`KIT_VERIFIED=pkg110-ddk-r1 files=17` 和 `SELF_CHECK=PASS shell_files=4 workflow=present target=PKG110`。
6. 如果出现 `files=16` 或找不到 `self_check.py`，说明该次 runner 检出的文件仍未包含完整修复。将完整 r3 源码 ZIP 的全部文件解压覆盖到仓库根目录（包括三个 TARGET 文件和隐藏的 .github 目录），提交这些文件（包含 `.github/workflows/build.yml`），然后通过 **Run workflow** 在该分支创建一次新运行。历史运行的 **Re-run jobs** 保留原来的 SHA/ref；仅重新执行旧运行不会取到新提交。
7. 在 **Show checkout identity** 或 **Verify checkout root** 日志中对照提交 SHA；失败诊断包的 `build_logs/checkout.txt` 也会记录 SHA 和相关受 Git 跟踪的文件。

本地使用 Git 客户端时，可先用以下命令核对已提交文件，确认输出中同时存在两个 Python 文件：

```sh
git ls-tree --name-only HEAD -- self_check.py verify_kit.py
git show HEAD:self_check.py
git rev-parse HEAD
```

网页上传时需要提交解压后的文件；仅在电脑文件管理器中看到这些文件，不代表它们已进入 Actions 使用的提交。

不要把整个 ZIP 当成单个文件上传，否则 GitHub 不会识别其中的工作流。Web 上传时隐藏目录容易遗漏，推荐使用 Git 客户端提交解压目录内容。

本包包含工作流和构建入口，未在你的 GitHub 仓库实际运行。现有 report.py 依赖目标 CRC/KCFI 等证据字段；目标画像目前尚未补齐这些字段，因此报告步骤可能失败。现有布局头中仍含待目标 BTF 核实的基线偏移。构建产物需经过进一步目标适配验证。
