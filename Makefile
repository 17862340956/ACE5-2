obj-m += cpuinfo_spoof.o
ccflags-y += -Werror=incompatible-pointer-types -g -gdwarf-4 -fno-eliminate-unused-debug-types
ccflags-y += -I$(src)
KDIR ?= $(error KDIR must point to the prepared android14-6.1 output)
MDIR := $(realpath $(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
.PHONY: all clean
all:
	@test -s "$(KDIR)/.config" || { echo "Missing DDK .config"; exit 1; }
	@test -s "$(KDIR)/Module.symvers" || { echo "Missing DDK Module.symvers"; exit 1; }
	@grep -qx 'CONFIG_MODVERSIONS=y' "$(KDIR)/.config" || { echo "MODVERSIONS required"; exit 1; }
	@grep -qx 'CONFIG_CFI_CLANG=y' "$(KDIR)/.config" || { echo "KCFI required"; exit 1; }
	@grep -qx 'CONFIG_COMPAT=y' "$(KDIR)/.config" || { echo "Target COMPAT layout required"; exit 1; }
	@grep -qx 'CONFIG_SHADOW_CALL_STACK=y' "$(KDIR)/.config" || { echo "Target shadow call stack required"; exit 1; }
	@mkdir -p "$(MDIR)/build_logs"
	+sh "$(MDIR)/prepare_ddk.sh" "$(KDIR)"
	$(MAKE) -C $(KDIR) M=$(MDIR) modules
	@cp "$(KDIR)/.config" "$(MDIR)/build_logs/ddk.config"
	@cp "$(KDIR)/Module.symvers" "$(MDIR)/build_logs/Module.symvers"
	@sha256sum "$(KDIR)/.config" "$(KDIR)/Module.symvers" > "$(MDIR)/build_logs/ddk-inputs.sha256"
clean:
	$(MAKE) -C $(KDIR) M=$(MDIR) clean
