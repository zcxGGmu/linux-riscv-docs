# RISC-V IOMMU Dirty Page Logging (DPL) Proposal of Work

# Introduction

The IOMMU G-stage Dirty Page Logging feature extends the AMO_HWAD capability to record dirty page addresses during the IOHGATP page table walk (PTW). Whenever the PTW updates the dirty bit, the corresponding Guest Physical Address (GPA) and IOHGATP values are logged separately into the GPA and IOHGATP buffers, respectively. Similar to ARM’s FEAT_HDBSS or INTEL’s PML in CPU.

# Why Existing Extensions Are Insufficient?

The existing IOMMU specification and its AMO_HWAD mechanisms (similar to ARM’s FEAT_DBM or INTEL’s EPT Dirty Bit) do not provide any hardware-assisted dirty page logging (similar to ARM’s FEAT_HDBSS or INTEL’s PML) for G-stage translations.

# Definitions

- HDBSS - Hardware Dirty State Tracking Structure of ARM
- PML - Page Modifications Logging of INTEL
- DBM - Dirty Bit Modifier from ARM’s Hardware update of the access flag and dirty state
- EPT Dirty Bit - Extended Page Tables Dirty Bit of INEL
- IOHGATP - IO Hypervisor Guest Address Translation and Protection of RISC-V IOMMU
- GPA - Guest Physical Address
- AMO_HWAD - Atomic Memory Operations for Hardware Access & Dirty bits of RISC-V IOMMU

# Background

Live migration is a critical capability in modern data centers and cloud computing environments, enabling the seamless migration of running virtual machines (VMs) between physical hosts without service interruption and supporting flexible cloud resource scheduling. The process typically comprises two phases: pre-copy (transferring memory pages from the source to the target while the VM executes on the source host) and post-copy (fetching missing pages from the source host after the VM cutover, triggered by page faults during execution).

In the pre-copy phase of VM live migration, advanced hardware dirty logging features such as ARM’s FEAT_HDBSS (Hardware Dirty State Tracking Structure) and Intel’s PML (Page Modification Logging) have become standard. These features allow the processor to automatically append the Guest Physical Address (GPA) of any dirtied page to a dedicated hardware-managed log buffer or queue whenever a write updates the dirty state in the second-stage page table (stage-2 on ARM, EPT on Intel). This process occurs transparently during the page-table walk, with no additional faults for permitted writes, thereby bypassing the performance penalties of software page faults and greatly improving migration efficiency while reducing host CPU load.

However, no commercially available IOMMU currently supports Dirty Logging functionality. Consequently, systems resort to software-based bitmap scanning to track device-induced dirty pages—a method that incurs substantial CPU overhead, disrupts migration throughput, and undermines the efficiency gains achieved by CPU-side hardware acceleration.

In the shared G-stage table between CPU and IOMMU scenarios [1], where pass-through DMA devices reuse the CPU’s G-stage page tables, the IOMMU must natively support Dirty Log functionality to collaborate with the CPU. Only through this hardware-coordinated approach can comprehensive, system-level dirty page tracking be realized across both CPU and device-initiated memory accesses.

To bridge this critical gap, we are proposing a G-stage Dirty Page Logging (DPL) extension for the RISC-V IOMMU [2]. It could be implemented by extending the AMO_HWAD capability during the iohgatp page table walk (PTW). When PTW updates the dirty bit, the corresponding Guest Physical Address (GPA) and iohgatp values are separately logged in the GPA and IOHGATP buffers. These buffers are maintained by the dirtylog queue, which uses several memory-mapped registers. The dirtylog queue follows the RISC-V IOMMU CQ/FQ/PQ design. Here is the diagram:

![image.png](https://lists.riscv.org/g/sig-datacenter/attachment/214/0)

[1] https://lore.kernel.org/linux-iommu/20231202091211.13376-1-yan.y.zhao@.../

[2] https://docs.google.com/document/d/1o0sCdeDmHcVrZypAX_vpnHcaj2sexjmWLql-i6S_mB0

# Objectives

This Task Group (TG) will define the RISC-V IOMMU Dirty Page Logging (DPL) extension, and here are the objectives:

- Determine memory-mapped register design.
- Determine in-memory data structure design.
- - Queue format
  - GPA buffer format
  - IOHGATP buffer format
- Set up a QEMU + Linux proof-of-concept prototype.
- Set up an HW prototype to demonstrate implementability.
- Cooperate with the CPU Dirty Page Logging TG and unify the GPA buffer format.