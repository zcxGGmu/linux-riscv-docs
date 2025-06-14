# RISC-V Qemu环境部署

主机环境建议 ubuntu22.04

* [RISC-V IOMMU Experiment](https://github.com/tjeznach/docs/tree/master/riscv-iommu)

  > 参考该RISC-V IOMMU的环境配置，注意内核配置项和qemu启动项
  >
  > qemu配置参考：https://www.qemu.org/docs/master/specs/riscv-iommu.html#riscv-iommu
  >
  > 注：此文档没有及时维护，需自行解决构建问题

* [RISC-V Perf](https://github.com/rajnesh-kanwal/linux/wiki/Running-CTR-basic-demo-on-QEMU-RISC%E2%80%90V-Virt-machine)

  > 项目3，参考此文档构建perf，由于交叉编译perf问题较多，所以首先构建原生的 `ubuntu-riscv`，然后基于此环境编译构建perf。 

---

项目1、2也可以使用这个更简洁的版本（项目3不能使用该环境），这是一个轻量级的RISC-V虚拟环境的构建流程：

* [KVM RISCV64 on QEMU](https://github.com/kvm-riscv/howto/wiki/KVM-RISCV64-on-QEMU)

  > 中文：https://tinylab.org/riscv-kvm-qemu-spike-linux-usage/
  >
  > 注意，此项目不需要在RISC-V宿主机虚拟环境中启用一台kvm虚拟机，涉及到kvm的组件可忽略，但这并不复杂，建议按文档完整部署一遍。

---

项目2，需要在本地交叉编译 `iommu-selftests`，再传入riscv-qemu环境中运行：

```shell
cd ./linux
export LDFLAGS="-static"
export CROSS_COMPILE=riscv64-unknown-linux-gnu-
make headers
make -C tools/testing/selftests/iommu TARGETS=riscv
```

