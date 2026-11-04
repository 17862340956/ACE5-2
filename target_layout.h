/* PKG110 target profile; offsets observed from target BTF where available. */
#ifndef PKG110_TARGET_LAYOUT_H
#define PKG110_TARGET_LAYOUT_H
#define TARGET_BTF_SHA256 "3e689a4312d2fea4a7a053ccf1d0d48bd6922f84e3006ba11e073d47a8e42422"
#define TARGET_UTS_NAME_OFFSET 0U
#define TARGET_DEVICE_ID_OFFSET 764U
#define TARGET_DENTRY_INODE_OFFSET 48U
#define TARGET_INODE_MODE_OFFSET 0U
#define TARGET_INODE_SB_OFFSET 40U
#define TARGET_INODE_INO_OFFSET 64U
#define TARGET_SB_MAGIC_OFFSET 96U
#define TARGET_RWSEM_BYTES 64U
#define PI_VFS_INODE_OFFSET 72U
#define PI_PDE_OFFSET 24U
#define PDE_BYTES 176U
#define PDE_OPS_OFFSET 48U
#define PDE_LOW_INO_OFFSET 92U
#define PDE_PARENT_OFFSET 120U
#define PDE_NAME_OFFSET 160U
#define PDE_MODE_OFFSET 168U
#define PDE_FLAGS_OFFSET 170U
static_assert(sizeof(void *) == 8);
static_assert(sizeof(struct new_utsname) == 390);
static_assert(offsetof(struct new_utsname, release) == 130);
static_assert(sizeof(struct proc_ops) == 96);
static_assert(offsetof(struct proc_ops, proc_flags) == 0);
static_assert(offsetof(struct proc_ops, proc_open) == 8);
static_assert(offsetof(struct proc_ops, proc_read) == 16);
static_assert(offsetof(struct proc_ops, proc_read_iter) == 24);
static_assert(offsetof(struct proc_ops, proc_write) == 32);
static_assert(offsetof(struct proc_ops, proc_lseek) == 40);
static_assert(offsetof(struct proc_ops, proc_release) == 48);
static_assert(offsetof(struct proc_ops, proc_poll) == 56);
static_assert(offsetof(struct proc_ops, proc_ioctl) == 64);
#ifdef CONFIG_COMPAT
static_assert(offsetof(struct proc_ops, proc_compat_ioctl) == 72);
#endif
static_assert(offsetof(struct proc_ops, proc_mmap) == 80);
static_assert(offsetof(struct proc_ops, proc_get_unmapped_area) == 88);
static_assert(sizeof(struct attribute) == 16);
static_assert(offsetof(struct attribute, name) == 0);
static_assert(offsetof(struct attribute, mode) == 8);
static_assert(sizeof(struct device_attribute) == 32);
static_assert(offsetof(struct device_attribute, attr) == 0);
static_assert(offsetof(struct device_attribute, show) == 16);
static_assert(offsetof(struct device_attribute, store) == 24);
static_assert(sizeof(struct freq_attr) == 32);
static_assert(offsetof(struct freq_attr, attr) == 0);
static_assert(offsetof(struct freq_attr, show) == 16);
static_assert(offsetof(struct freq_attr, store) == 24);
static_assert(sizeof(struct seq_operations) == 32);
static_assert(offsetof(struct seq_operations, start) == 0);
static_assert(offsetof(struct seq_operations, stop) == 8);
static_assert(offsetof(struct seq_operations, next) == 16);
static_assert(offsetof(struct seq_operations, show) == 24);
#endif
