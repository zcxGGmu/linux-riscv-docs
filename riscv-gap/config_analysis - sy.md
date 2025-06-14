# Kconfig 架构间差异
## X86支持，ARM、RISCV不支持，非dirvers
### 功能差距
#### 1. 内存管理
##### 1.1 多级页表 
* CONFIG_3_LEVEL_PG
  * path：arch/x86/um/Kconfig
  * 功能说明：   
    启用时，内核为页表采用三层层次结构，这样在具有大地址空间的系统中进行有效的内存管理。三级页表将使UML拥有超过4G的物理内存。所有不能直接映射的内存都将被视为高内存。这个配置选项影响虚拟内存的组织和访问方式。
  * RISC-V相关支持：
    RISC-V架构支持灵活的页表配置，允许不同级别的页表层次结构来适应不同的内存寻址需求。具体来说，基于rv32i的系统可以拥有最多34位的物理地址和一个三层页表，而基于rv64i的系统可以支持多个具有更大物理地址空间的虚拟地址空间。[Paging and the MMU in the RISC-V Linux Kernel](https://www.sifive.cn/blog/all-aboard-part-9-paging-and-mmu-in-risc-v-linux-kernel)

* CONFIG_X86_5LEVEL
  * path：arch/x86/Kconfig
  * 功能说明：  
    5 级分页支持访问更大的地址空间：高达 128 PiB 的虚拟地址空间和 4 PiB 的物理地址空间。它将受到未来英特尔 CPU 的支持。启用了该选项的内核可以在支持 4 级或 5 级分页的计算机上启动。

##### 1.2 线性地址掩码 
* CONFIG_ADDRESS_MASKING
  * path：arch/x86/Kconfig
  * 功能说明：    
    线性地址掩码 （LAM） 修改应用于64 位线性地址的检查，允许软件将未翻译的地址位用于元数据。该功能可用于高效的地址清理程序 （ASAN）实施和 JIT 中的优化。
  * RISC-V相关支持：
    对线性地址掩码的具体实现和支持可能会因特定的RISC-V cpu及其配套的软件生态系统而异。有可能在某些RISC-V配置和实现中找到对该特性的支持？

##### 1.3 NUMA节点拓扑检测
* CONFIG_AMD_NUMA
  * path：arch/x86/Kconfig
  * 功能说明：  
    如果有一个多处理器AMD系统，应该在这里说Y。这使用旧方法直接从Opteron的内置Northbridge读取NUMA配置。  
    建议改用 X86_64_ACPI_NUMA，如果两者都编译进来，它也会优先。

    代码实现与 L3 cache有关。
  * RISC-V相关支持：
    一些RISC-V处理器有L3缓存，如[Ventana RISC-V CPUs](https://www.nextplatform.com/2023/02/02/the-first-risc-v-shot-across-the-datacenter-bow/)

##### 1.4 内存热插拔
* CONFIG_ARCH_HAS_ADD_PAGES
  * path：arch/x86/Kconfig
  * 功能说明：  
    在运行时期间添加内存页，需要体系结构提供动态添加页面的实现，通常用于内存热插拔等场景。

##### 1.5 内存映射
* CONFIG_ARCH_USES_PG_UNCACHED
  * path：arch/x86/Kconfig
  * 功能说明：  
    当启用该选项时，该选项允许架构利用PG_uncached标志，表明一个页面已被映射为非缓存。这个标志可以在内核代码的各个部分引用，例如include/linux/page-flags.h，以处理与非缓存内存映射相关的特定行为。
  * RISC-V相关支持：
    可以使用PG_uncached标志,来表明页面已被映射为非缓存，这对于特定的内存映射要求或优化非常有用。  
    从实现代码来看，与架构无关，但该配置项未在其它架构下定义。

* CONFIG_EFI_FAKE_MEMMAP
  * path：arch/x86/Kconfig
  * 功能说明：  
    启用后，内核根据系统的物理内存大小生成一个假内存映射。这允许EFI运行时服务(如查询内存映射信息或分配内存)按预期运行，即使固件没有提供准确的内存映射细节。在固件缺乏适当的EFI内存映射支持或提供不正确信息的情况下，启用CONFIG_EFI_FAKE_MEMMAP可能会有所帮助。然而，必须注意的是，使用假内存映射可能会导致EFI运行时服务的不准确或限制，因为它不反映系统的实际内存布局。
  * RISC-V相关支持：  
    RISC-V架构本身不支持可扩展固件接口(Extensible Firmware Interface, EFI)运行时服务。EFI主要用于x86架构和一些基于arm的系统。  
    RISC-V通常依赖于其他引导机制，例如OpenSBI(开放监督二进制接口)或类似的固件，用于引导和初始化任务。

##### 1.7 动态调整
* CONFIG_DYNAMIC_MEMORY_LAYOUT
  * path：arch/x86/Kconfig
  * 功能说明：
    启用后，内核可以在系统初始化期间动态调整内存布局参数，例如内核代码、数据和其他内存区域的位置。启用CONFIG_DYNAMIC_MEMORY_LAYOUT提供了针对不同硬件配置和系统工作负载进行内存管理和优化的灵活性。它允许内核适应不同的内存约束，并根据运行时条件优化内存使用。这个特性在内存资源有限的嵌入式系统中特别有用，或者在具有异构内存体系结构的系统中，不同的内存区域可能具有不同的特征。

* CONFIG_DYNAMIC_PHYSICAL_MASK
  * path：arch/x86/Kconfig
  * 功能说明：  
    内核可以在引导过程中根据检测到的物理内存量动态调整物理地址限制。这确保了内核可以寻址所有可用的物理内存，而不受固定物理地址限制的约束。内核可以更好地利用可用内存资源，而不会浪费地址空间或遇到寻址限制。它增强了内核处理各种硬件配置的能力，而不需要手动调整或重新编译。

##### 1.8 高内存支持
* CONFIG_HIGHMEM64G
  * path：arch/x86/Kconfig
  * 功能说明：  
    启用后，它允许内核寻址和管理最高可达64GB或更高的内存，具体取决于系统的能力。高内存支持对于具有大量RAM的系统(例如服务器和高性能计算集群)是必不可少的，因为它确保内核能够有效地访问和利用所有可用内存。

##### 1.9 本地描述符表
* CONFIG_MODIFY_LDT_SYSCALL
  * path：arch/x86/Kconfig
  * 功能说明：  
    modify_ldt系统调用提供了在LDT中创建、修改和删除条目的功能，LDT是x86架构用来管理内存访问的段描述符的数据结构。modify_ldt系统调用可用于各种目的，包括实现自定义内存保护机制、管理每个线程的内存访问权限，以及与依赖于基于ldt的内存管理的遗留软件进行接口。然而，modify_ldt系统调用被认为是遗留的，在现代应用程序中不常用。大多数现代软件都依赖于x86架构上的标准内存管理单元(MMU)和虚拟内存系统(VMS)提供的更灵活、更强大的内存管理功能。

##### 1.10 物理地址
* CONFIG_PHYSICAL_ALIGN
  * path：arch/x86/Kconfig
  * 功能说明：  
    如果引导加载程序在未对齐的地址加载内核并设置了CONFIG_RELOCATABLE，则内核将自身移动到与上述值对齐的最近地址并从那里运行。  
    如果引导加载程序在未对齐的地址加载内核并且未设置CONFIG_RELOCATABLE，则内核将忽略运行时加载地址，并将自身解压缩到已编译的地址并从那里运行。  
    编译内核的地址已经满足上述对齐限制。因此，最终结果是内核从满足对齐限制的物理地址运行。  
    [patch](https://lkml.indiana.edu/hypermail/linux/kernel/0610.0/0845.html)

* CONFIG_PHYSICAL_START
  * path：arch/x86/Kconfig
  * 功能说明：  
    用于设置加载内核的物理地址

* CONFIG_RANDOMIZE_MEMORY
  * path：arch/x86/Kconfig
  * 功能说明：  
    定义在内核内存随机化期间添加到现有物理内存大小的填充（以 TB 为单位）。它对于内存热插拔支持很有用，但会降低可用于地址随机化的熵。

##### 1.11 可纠正错误收集器
* CONFIG_RAS_CEC
  * path：arch/x86/ras/Kconfig
  * 功能说明：  
    这是一个小型缓存，它收集每个 4K页 PFN 的可纠正内存错误，并计算其重复发生次数。一旦PFN 的计数器溢出，就会尝试软离线该页面，因为认为这意味着它已经达到了相对较高的错误计数，如果不再使用它，这可能是最好的。
  note：如果平台没有ECC DIMM，并且没有在 BIOS 中启用 DRAM ECC 检查，则这绝对没用。

##### 1.12 内存保护
* CONFIG_X86_INTEL_MEMORY_PROTECTION_KEYS
  * path：arch/x86/Kconfig
  * 功能说明：  
    内存保护密钥提供了一种强制实施基于页面的保护的机制，但在应用程序更改保护域时不需要修改页表。

#### 2. 内核热升级
* CONFIG_CRASH_HOTPLUG
  * path：kernel/Kconfig.kexec
  * 功能说明：  
    在系统配置更改时更新crash elfcorehdr。此特性允许在系统配置发生变化时动态更新崩溃转储机制，例如CPU和内存的热插拔事件。如果选择此选项，内核将有效地处理CPU和内存热拔插/拔插事件，以生成和分析崩溃转储，确保即使在这种动态更改期间也能准确捕获系统状态。
  [patch](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=d68b4b6f307d155475cce541f2aee938032ed22e)
  * RISC-V相关支持：  
    RISC-V架构支持在kexec启动后[生成崩溃转储](https://patchwork.kernel.org/project/linux-riscv/patch/20210405085712.1953848-6-mick@ics.forth.gr/),使用特定于平台的代码来定位内存中的[elf core head](https://lkml.iu.edu/hypermail/linux/kernel/2106.1/09915.html)

* CONFIG_KEXEC_JUMP
  * path：kernel/Kconfig.kexec
  * 功能说明：  
    允许从当前运行的内核引导到新内核，而不需要经过整个系统重新引导过程。例如，它可以用于测试新的内核版本、执行系统升级或从内核崩溃中恢复，而不会中断其他正在运行的进程。要使用kexec跳转，通常需要一个用户空间实用程序(如kexec-tools)将新的内核映像加载到内存中，并触发kexec跳转操作。一旦启动，当前运行的内核将为内核切换做好准备，将新的内核映像加载到内存中，并执行它，从而有效地将正在运行的内核替换为新的内核。

#### 3. 虚拟化
##### 3.1 Guest 支持
* CONFIG_ACRN_GUEST
  * path：arch/x86/Kconfig
  * 功能说明：  
    为嵌入式IoT用例设计的轻量级Hypervisor。此选项允许在 ACRN 虚拟机管理程序中作为客户机运行 Linux。
  * RISC-V相关支持：  
    目前正在努力将ACRN Hypervisor移植到非英特尔架构，包括RISC-V。虽然这仍然处于[计划阶段](https://projectacrn.github.io/latest/projects/multi-arch-support.html)，但有专门用于此任务的[存储库](https://github.com/intel/acrn-riscv)，表明该领域的积极开发。

* CONFIG_HYPERVISOR_GUEST
  * path：arch/x86/Kconfig
  * 功能说明：  
    支持在hypervisor下作为客户机运行Linux

* CONFIG_JAILHOUSE_GUEST
  * path：arch/x86/Kconfig
  * 功能说明：  
    Jailhouse是一个分区管理程序，它允许在系统上创建多个隔离的“单元”(分区)，每个单元运行自己的操作系统。这些单元彼此严格隔离，并对硬件资源的访问进行控制，从而为安全关键型或安全敏感型工作负载提供强大的隔离。
  * RISC-V相关支持：  
    [RISC-V support for Jailhouse](https://www.mail-archive.com/jailhouse-dev@googlegroups.com/msg11168.html)

* CONFIG_PVH
  * path：arch/x86/Kconfig
  * 功能说明：  
    支持运行 PVH 客户机，此选项为 x86/HVM 直接引导 ABI 中指定的客户机虚拟机启用 PVH 入口点。

* CONFIG_KVM_GUEST
  * path：arch/x86/Kconfig
  * 功能说明：  
    支持kvm中将Linux作为客户机OS运行

##### 3.2 KVM特性
* CONFIG_HAVE_KVM_DIRTY_RING_TSO
  * path：virt/kvm/Kconfig
  * 功能说明：  
    当启用时，它表示内核具有必要的基础设施来实现脏环特性，以便在KVM子系统中有效地处理TSO数据包。该功能通过跟踪和更新仅传输数据的修改段来优化TSO数据包的处理，从而减少开销并提高性能。如果禁用，内核不支持KVM子系统中TSO包的脏环特性，可以使用替代机制来处理TSO包。

* CONFIG_KVM_AMD_SEV
  * path：virt/kvm/Kconfig
  * 功能说明：  
    AMD安全加密虚拟化(SEV): SEV是一项通过加密每个客户虚拟机的内存来增强虚拟机安全性的特性，将其与其他虚拟机和hypervisor隔离开来。

* CONFIG_ARCH_CPUIDLE_HALTPOLL
  * path：arch/x86/Kconfig
  * 功能说明：  
    在执行客户端轮询时，没有必要也执行主机端轮询。因此，在加载cpuidle-haltpoll驱动程序时，通过新的MSR接口禁用主机端轮询。
    [patch](https://patchwork.kernel.org/project/kvm/patch/20190701185528.230754447@asus.localdomain/)

* CONFIG_KVM_EXTERNAL_WRITE_TRACKING
  * path：arch/x86/kvm/Kconfig
  * 功能说明：  
    KVM使用外部机制跟踪对客户机内存的写操作。为外部工具或模块提供一个接口，以监视和跟踪客户机操作系统对其内存执行的写操作。这有助于识别潜在的内存损坏问题、分析系统行为以及调试客户机内核或应用程序代码。由于涉及到额外的跟踪机制，启用此配置选项可能会引入一些开销。然而，在某些场景中，特别是在开发和测试阶段，增强调试和监视功能的好处可能超过性能影响。

* CONFIG_KVM_PROVE_MMU
  * path：arch/x86/kvm/Kconfig
  * 功能说明：  
    kvm启用额外的MMU校验。引入了额外的验证机制，以确保KVM子系统中与mmu相关的操作的正确性。这些机制有助于检测和防止潜在问题，如内存损坏、无效页表项或其他可能危及系统稳定性或安全性的mmu相关错误。

* CONFIG_KVM_SMM
  * path：arch/x86/kvm/Kconfig
  * 功能说明：  
    KVM启用对系统管理模式(SMM)。系统管理模式是x86处理器中的一种特殊操作模式，它允许固件以更高的特权级别执行某些操作，独立于操作系统和系统上运行的其他软件。

* CONFIG_X86_SGX_KVM
  * path：arch/x86/kvm/Kconfig
  * 功能说明：  
    Software Guard eXtensions （SGX） 虚拟化

* CONFIG_KVM_XEN
  * path：arch/x86/kvm/Kconfig
  * 功能说明：  
    KVM中支持Xen半虚拟化

##### 3.3 PARAVIRT半虚拟化  
一种在虚拟化环境中使用的技术，它允许guest操作系统直接与hypervisor或虚拟化平台通信，从而提高性能和效率。半虚拟化的一个方面是为某些操作(如计时)提供优化的接口。

* CONFIG_PARAVIRT_CLOCK
  * path：arch/x86/Kconfig
  * 功能说明：  
    半虚拟化时钟管理，当启用时，允许客户机操作系统从底层虚拟化基础设施获得准确的时间信息，这有助于提高虚拟机中对时间敏感的操作的性能和可靠性。在需要精确计时的虚拟化环境中，启用通常是有益的，例如云计算平台和数据中心虚拟化部署。它允许客户机操作系统利用底层管理程序或虚拟化平台的功能来实现更好的计时精度和性能。

* CONFIG_PARAVIRT_DEBUG
  * path：arch/x86/Kconfig
  * 功能说明：  
    当启用时，内核包含额外的调试特性和功能，专门用于诊断和排除与半虚拟化相关的问题。这些特性可能包括日志记录、跟踪和其他调试机制，这些机制提供了对客户机操作系统和管理程序之间交互的深入了解。在虚拟环境的开发、测试和故障排除过程中，非常有用。

* CONFIG_PARAVIRT_SPINLOCKS
  * path：arch/x86/Kconfig
  * 功能说明：  
    半虚拟化自旋锁通过利用hypervisor的帮助来优化虚拟化环境中的自旋锁操作。内核使用hypervisor提供的半虚拟化自旋锁实现，而不是默认的自旋锁实现。这允许管理程序优化自旋锁操作，以便在虚拟化环境中获得更好的性能和可伸缩性。提高在虚拟化环境中运行的工作负载的性能，特别是在多个虚拟cpu (vcpu)争用自旋锁的场景下。

* CONFIG_PARAVIRT_XXL
  * path：arch/x86/Kconfig
  * 功能说明：  
    更大的半虚拟化特性集

##### 3.4 XEN虚拟化
* CONFIG_XEN_PV
  * path：arch/x86/xen/Kconfig
* CONFIG_XEN_PVH
  * path：arch/x86/xen/Kconfig
* CONFIG_XEN_PVHVM
  * path：arch/x86/xen/Kconfig
* CONFIG_XEN_PV_DOM0
  * path：arch/x86/xen/Kconfig

##### 3.5 其它特性
* CONFIG_VBOXSF_FS
  * path：fs/vboxsf/Kconfig
  * 功能说明：  
    VirtualBox 客户机共享文件夹 （vboxsf） 支持。  
    VirtualBox主机可以与guest共享文件夹，这个驱动程序实现了Linux-guest端，允许主机导出的文件夹在Linux下挂载。
  * RISC-V相关支持：  
    目前，还没有专门为RISC-V架构量身定制的VirtualBox官方版本。VirtualBox主要设计运行在基于x86的平台上，目前还没有RISC-V架构的官方发布或移植。

* CONFIG_X86_VMX_FEATURE_NAMES
  * path：arch/x86/Kconfig.cpu
  * 功能说明：  
    在引导过程中显示VMX(虚拟机扩展)功能名称。  
    VMX是指Intel的虚拟化技术(VT-x)特性。启用此选项允许内核在引导过程中列出处理器支持的VMX特性的名称，从而提供对CPU虚拟化功能的可见性。

#### 4. 安全特性
##### 4.1 CPU漏洞缓解措施
* CONFIG_CPU_IBPB_ENTRY
  * path：arch/x86/Kconfig
  * 功能说明：  
    启用 IBPB，编译支持 retbleed=ibpb 缓解的内核。  
    IBPB，即间接分支预测屏障，是现代处理器中的一种微架构特性。它旨在减轻某些类型的安全漏洞，特别是与Spectre Variant 2相关的安全漏洞。在分支的目标已知并得到验证之前，IBPB防止在间接分支指令之后猜测执行指令。在不同的执行上下文(如用户模式和内核模式)之间切换时刷新推测执行管道，以维护安全边界，这有助于防止对敏感信息的未经授权访问。
  * RISC-V相关支持：  
    目前，RISC-V架构没有直接等同于x86处理器中的IBP或IBRS功能。
    然而，RISC-V作为一个开放的体系结构，允许实现各种安全特性，包括缓解诸如x86处理器中的IBPB和IBRS所解决的推测性执行漏洞。RISC-V社区内的一些计划侧重于增强安全功能。例如，研究人员和开发人员正在探索通过结合针对RISC-V架构的类似机制或替代方法来减轻推测性执行漏洞的技术。虽然IBPB和IBRS是特定于x86架构的，但RISC-V生态系统可能采用类似的或新颖的安全特性来解决类似的问题。随着RISC-V架构的发展和成熟，很可能会开发安全功能来减轻推测执行漏洞，并将其集成到RISC-V实现中。

* CONFIG_CPU_IBRS_ENTRY
  * path：arch/x86/Kconfig
  * 功能说明：  
    间接分支限制推测(Indirect Branch Restricted Speculation, IBRS)。IBRS是一种Spectre Variant 2缓解技术，有助于防止推测性执行漏洞。当启用时，它确保CPU通过限制进入内核时对间接分支指令的猜测来减轻Spectre Variant 2漏洞。这个特性对于易受基于幽灵的攻击的系统尤其重要。

* CONFIG_CPU_SRSO
  * path：arch/x86/Kconfig
  * 功能说明：  
    启用时，它指示处理器支持推测返回堆栈覆盖(SRSO)缓解。SRSO缓解旨在通过引入防止返回堆栈的推测覆盖的保护措施来防止攻击者利用与推测执行相关的漏洞，从而增强系统安全性。

* CONFIG_CPU_UNRET_ENTRY
  * path：arch/x86/Kconfig.cpu

##### 4.2 编译选项缓解措施
* CONFIG_NOINSTR_VALIDATION
  * path：lib/Kconfig.debug
  * 功能说明：  
    编译时检查和编译器选项：指令指针检查。
    当启用时，内核对指令指针执行验证检查，以确保它们指向有效的代码位置。此验证有助于检测执行流中的潜在异常或损坏，这些异常或损坏可能由硬件故障、软件错误或恶意攻击引起。通过验证指令指针，内核提高了系统的可靠性和安全性。相反，当禁用时，内核会跳过指令指针验证检查。禁用此特性可能会略微提高性能，因为消除了执行验证检查的开销。然而，它也增加了从无效或意外位置执行代码的风险，这可能导致系统不稳定或安全漏洞。

* CONFIG_RETHUNK
  * path：arch/x86/Kconfig
  * 功能说明：  
    使用 return-thunks 编译器选项编译内核，通过避免返回猜测来防止内核到用户的数据泄漏。需要具有 -mfunction-return=thunk-extern支持的编译器才能获得全面保护。内核可能运行速度较慢。

* CONFIG_RETPOLINE
  * path：arch/x86/Kconfig
  * 功能说明：  
    使用 retpoline 编译器选项编译内核，通过避免推测性间接分支来防止内核到用户的数据泄露。需要具有 -mindirect-branch=thunk-extern支持的编译器才能获得全面保护。内核可能运行速度较慢。

* CONFIG_SLS
  * path：arch/x86/Kconfig
  * 功能说明：  
    使用直线推测选项编译内核，以防止直线推测。内核映像可能稍大一些。

##### 4.2 其它安全缓解技术
* CONFIG_PAGE_TABLE_ISOLATION
  * path：arch/x86/Kconfig
  * 功能说明：  
    删除用户模式下的内核映射。  
    页表隔离是一种安全缓解技术，旨在防止某些类型的推测性执行漏洞，如Meltdown和Spectre的变体。这些漏洞可能允许恶意程序通过利用CPU推测执行机制中的缺陷来访问敏感数据。当启用时，内核通过将内核页表与用户空间页表隔离来实现页表隔离。这种隔离可以防止用户空间进程直接访问内核内存，从而降低泄露敏感信息的风险。启用会增加内核内存管理操作的开销，因为它涉及到在内核和用户空间页表之间进行额外的检查和切换。

* CONFIG_HAVE_ATOMIC_IOMAP
  * path：arch/x86/Kconfig
  * 功能说明：  
    支持原子I/O映射操作。原子I/O映射操作通常用于设备驱动程序和其他内核组件，以确保自动执行I/O内存上的某些操作，而不会受到其他进程或硬件的干扰。这有助于在访问硬件寄存器和其他I/O内存位置时保持数据一致性和完整性。。

* CONFIG_GDS_FORCE_MITIGATION
  * path：arch/x86/Kconfig
  * 功能说明：  
    Force GDS 缓解。与“全局芯片安全”(GDS)功能相关的内核配置选项，旨在缓解硬件中的某些安全漏洞。

* CONFIG_X86_INTEL_USERCOPY
  * path：arch/x86/Kconfig.cpu
  * 功能说明：  
    特定于Intel体系结构的用户拷贝检查。此特性有助于防止与在用户空间和内核空间之间复制数据相关的安全漏洞。启用此选项可确保内核在数据复制操作期间执行额外的检查，以验证用户提供的内存地址和大小，从而通过降低与缓冲区溢出和其他内存相关漏洞相关的风险来增强系统安全性。

* CONFIG_X86_UMIP
  * path：arch/x86/Kconfig
  * 功能说明：  
    用户模式指令防护 （UMIP） 是某些 x86 处理器中的一项安全功能。启用后，SGDT、SLDT、SIDT、SMSW 或 STR 指令在用户模式下执行时，会发出一般保护故障。这些说明不必要地公开有关硬件状态的信息。绝大多数应用程序不使用这些说明。

* CONFIG_INTEL_TDX_GUEST
  * path：arch/x86/Kconfig
  * 功能说明：  
    TDX是英特尔引入的一种基于硬件的安全特性，它为运行在英特尔处理器上的虚拟机提供隔离。

* CONFIG_INTEL_TXT
  * path：security/Kconfig
  * 功能说明：  
    Intel可信执行技术(TXT)。英特尔TXT是一种基于硬件的安全特性，旨在通过建立度量信任根(RTM)和在启动过程中提供系统组件的完整性验证来增强平台安全性。

#### 5. 跟踪特性
##### 5.1 调用深度跟踪
* CONFIG_CALL_DEPTH_TRACKING
  * path：arch/x86/Kconfig
  * 功能说明：  
    此特性有助于减轻某些安全漏洞，例如英特尔SKL返回-推测-缓冲区(RSB)下溢问题。默认情况下，这种缓解是关闭的，但是启用它可以通过跟踪内核中函数调用的深度来提供针对潜在攻击的额外保护。启用后，内核会跟踪调用堆栈深度，这有助于防止利用与推测执行相关的漏洞或依赖于操纵调用堆栈行为的其他攻击向量。arch/x86/include/asm/nospec-branch.h
  * RISC-V相关支持：  
    RISC-V目前没有专门的硬件支持跟踪。

##### 5.2 调用库支持
* CONFIG_CALL_THUNKS
  * path：arch/x86/Kconfig
  * 功能说明：  
    调用库是由编译器插入的小代码片段，用于处理函数调用。在某些情况下，例如调用具有不兼容调用约定的函数或跨不同代码段进行调用时，这些功能可能是必要的。启用此选项允许内核在编译期间根据需要生成和使用调用库，从而确保函数调用的兼容性和正确行为。

##### 5.3 细粒度间接分支跟踪
* CONFIG_FINEIBT
  * path：arch/x86/Kconfig
  * 功能说明：  
    启用后，此特性在跟踪间接分支时提供了更细的粒度，这有助于识别潜在的安全漏洞。但是，启用CONFIG_FINEIBT可能会有一些性能开销，因为它涉及到额外的跟踪和验证机制。总的来说，启用CONFIG_FINEIBT通过提供更好的保护来抵御某些类型的攻击，从而增强了系统的安全性，但这可能会以牺牲某些性能为代价。

##### 5.4 内存映射I/O跟踪
* CONFIG_MMIOTRACE
  * path：kernel/trace/Kconfig
  * 功能说明：  
    MMIO跟踪通常涉及检测内核以拦截MMIO访问事件并记录相关信息，例如访问的地址、数据值和上下文信息。这些跟踪数据可以用于各种目的，比如识别性能瓶颈、诊断与硬件相关的问题，或者验证设备驱动程序的正确行为。

##### 5.5 内核堆栈跟踪
* CONFIG_UNWINDER_ORC
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    ORC（Oops Rewind Capability）展开器。它使用自定义数据格式，该格式是DWARF 呼叫帧信息标准的简化版本。此展开器在中断输入帧中比帧指针展开器更准确。与帧指针相比，它还使整个内核的性能提高了 5-10%。启用此选项将使内核的运行时内存使用量增加大约 2-4MB，具体取决于内核配置。

* CONFIG_UNWINDER_GUESS
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    扫描堆栈并报告它找到的每个内核文本地址。它报告的某些地址可能不正确。虽然此选项经常产生误报，但在许多情况下它仍然有用。与其他放卷机不同，它没有运行时开销。

##### 5.6 暂停/恢复事件跟踪
* CONFIG_PM_TRACE_RTC
  * path：kernel/power/Kconfig
  * 功能说明：  
    可以在重新启动时将最后一个 PM 事件点保存在RTC 中，以便可以调试在挂起期间（或更常见的是恢复期间）挂起的计算机。

#### 6. 加密算法集
| Config                                   | path                    | function                 |
|------------------------------------------|-------------------------|--------------------------|
| CONFIG_AMD_MEM_ENCRYPT                   | arch/x86/Kconfig        | AMD 内存安全加密 （SME） |
| CONFIG_CRYPTO_AEGIS128_AESNI_SSE2        | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_AES_NI_INTEL               | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_ARIA_AESNI_AVX2_X86_64     | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_ARIA_AESNI_AVX_X86_64      | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_ARIA_GFNI_AVX512_X86_64    | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_BLAKE2S_X86                | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_BLOWFISH_X86_64            | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_CAMELLIA_AESNI_AVX2_X86_64 | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_CAMELLIA_AESNI_AVX_X86_64  | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_CAMELLIA_X86_64            | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_CAST5_AVX_X86_64           | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_CAST6_AVX_X86_64           | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_CHACHA20_X86_64            | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_CRC32C_INTEL               | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_CRC32_PCLMUL               | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_CRCT10DIF_PCLMUL           | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_CURVE25519_X86             | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_DES3_EDE_X86_64            | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_GHASH_CLMUL_NI_INTEL       | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_NHPOLY1305_AVX2            | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_NHPOLY1305_SSE2            | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_POLY1305_X86_64            | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_POLYVAL_CLMUL_NI           | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_SERPENT_AVX2_X86_64        | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_SERPENT_AVX_X86_64         | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_SERPENT_SSE2_586           | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_SERPENT_SSE2_X86_64        | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_SHA1_SSSE3                 | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_SHA256_SSSE3               | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_SHA512_SSSE3               | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_SM3_AVX_X86_64             | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_SM4_AESNI_AVX2_X86_64      | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_SM4_AESNI_AVX_X86_64       | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_TWOFISH_586                | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_TWOFISH_AVX_X86_64         | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_TWOFISH_X86_64             | arch/x86/crypto/Kconfig | CPU 加密算法             |
| CONFIG_CRYPTO_TWOFISH_X86_64_3WAY        | arch/x86/crypto/Kconfig | CPU 加密算法             |

目前，RISC-V cpu还没有标准的硬件加密算法集。然而，RISC-V cpu可以使用针对特定用例定制的指令或扩展来实现各种加密算法。
虽然RISC-V架构不包括AES专用指令，但许多RISC-V芯片包括集成的AES协处理器。例如:双核RISC-V 64位Sipeed-M1支持AES和SHA256。[基于RISC-V架构的ESP32- c(以及基于xtensa的ESP32)，支持AES, SHA, RSA, RNG, HMAC，数字签名和flash的XTS 128。Bouffalo Labs BL602/604 32位RISC-V支持各种AES和SHA变体。](https://en.wikipedia.org/wiki/AES_instruction_set#RISC-V_architecture)

#### 7. 特性优化
##### 7.1 电源相关
* CONFIG_ARCH_HAS_CPU_RELAX
  * path：arch/x86/Kconfig
  * 功能说明：  
    cpu_relax()函数向CPU提供提示，提示当前线程处于spin-wait循环中，允许CPU在等待事件时执行低功耗优化或其他任务。它影响内核的各个部分，包括电源管理和CPU空闲状态。

* CONFIG_AS_TPAUSE
  * path：arch/x86/Kconfig.assembler
  * 功能说明：  
    与支持TPAUSE指令的x86汇编语言相关。TPAUSE指令用于优化自旋循环和提高x86架构上的电源效率。启用CONFIG_AS_TPAUSE允许内核在适当的地方在汇编代码中使用TPAUSE指令。该特性增强了受支持的x86处理器的性能和电源管理能力。

##### 7.2 性能优化
* CONFIG_CALL_PADDING
  * path：arch/x86/Kconfig
  * 功能说明：  
    启用后，内核将向堆栈添加填充以对齐函数调用，这可以通过确保函数调用参数和返回地址的正确对齐来帮助提高性能。但是，启用此选项可能会增加堆栈使用和内存开销。默认情况下，通常禁用此选项以节省内存，但如果需要进行性能优化，则可以启用该选项。
    
* CONFIG_SCHED_MC_PRIO
  * path：arch/x86/Kconfig
  * 功能说明：  
    CPU 核心优先级调度程序支持。支持英特尔睿频加速 Max 技术 3.0 的 CPU 在制造时确定内核顺序，这允许某些内核达到比其他内核更高的睿频频率（运行单线程工作负载时）。启用此内核功能后，调度程序可以了解 CPU 内核的 TBM3（又名 ITMT）优先级顺序，并相应地调整调度程序的 CPU 选择逻辑，从而实现更高的整体系统性能。

#### 8. 调试功能
##### 8.1 调试信息输出
* CONFIG_CPA_DEBUG
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    此选项启用CPA子系统的调试输出，该子系统负责维护不同缓存之间的一致性，并确保虚拟和物理内存映射之间的一致性。启用后，它提供额外的调试信息，以帮助诊断与

* CONFIG_DEBUG_ENTRY
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    当启用此选项时，内核中会包含额外的调试代码，以便在内核进入和退出各种函数和代码路径时深入了解执行流。这些调试信息对于诊断与内核执行相关的问题很有价值，比如检测意外的函数调用、识别启动期间的执行顺序，或者分析运行时期间的系统行为。

* CONFIG_EARLY_PRINTK_DBGP
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    通过调试端口(DBGP)接口启用早期内核调试支持。允许内核在启动过程的早期(在初始化常规控制台驱动程序之前)输出调试消息。这种早期printk功能对于诊断引导过程早期(如硬件初始化或早期内核初始化阶段)发生的问题至关重要。
    DBGP 是一种标准化的调试通信接口，常见于嵌入式系统和某些架构中。它提供了一种与系统交互的方法，用于调试和故障排除。

* CONFIG_NMI_CHECK_CPU
  * path：lib/Kconfig.debug
  * 功能说明：  
    当 CPU 无法响应给定的回溯 NMI 时启用调试打印。这些打印提供了 CPU可能无法合法响应的一些原因，例如，如果处于脱机状态或设置了 ignore_nmis。

##### 8.2 自检
* CONFIG_DEBUG_IMR_SELFTEST
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    中断掩码寄存器(IMR)的自检。中断掩码寄存器用于屏蔽或取消系统上的中断。此自检代码有助于在系统初始化或运行时验证中断掩码寄存器的正确性和功能。

* CONFIG_DEBUG_NMI_SELFTEST
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    非屏蔽中断(Non-Maskable Interrupts, nmi)是一种特殊类型的中断，不能被软件屏蔽或禁用。它们通常用于需要立即注意的关键系统事件，例如硬件错误或系统故障。启用CONFIG_DEBUG_NMI_SELFTEST有助于在引导期间执行自检，从而确保内核中NMI机制的可靠性和正确性。如果在自测期间检测到任何问题，将提供适当的调试信息来帮助诊断和解决问题。该选项对于调试和诊断系统中与硬件相关的问题特别有用，因为它有助于验证NMI机制的正确功能，这对于处理关键系统事件至关重要。

##### 8.3 内核启动
* CONFIG_CMDLINE_BOOL
  * path：arch/x86/Kconfig
  * 功能说明：  
    启用后，它允许在引导时向内核传递命令行参数，提供各种选项和参数来配置内核行为或指定引导参数。这个选项通常在大多数内核配置中启用，以支持在引导过程中向内核传递参数，允许用户根据需要定制内核行为。

* CONFIG_CMDLINE_OVERRIDE
  * path：arch/x86/Kconfig
  * 功能说明：  
    启用后，它使内核能够忽略引导加载程序传递的命令行，而使用内核编译期间或通过其他方式配置的命令行。在需要确保始终使用特定的内核命令行参数的情况下，无论引导加载程序提供什么，这都很有用。

* CONFIG_DEBUG_BOOT_PARAMS
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    调试在启动过程中传递给内核的启动参数。启用该选项后，将提供与引导参数相关的额外调试信息，这对于诊断与引导相关的问题或分析引导过程中的内核行为非常有用。

* CONFIG_X86_VERBOSE_BOOTUP
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    启动解压缩阶段（例如 bzImage）的信息输出。如果禁用此功能，仍然会看到错误。如果要静默启动，请禁用此功能。

* CONFIG_PROVIDE_OHCI1394_DMA_INIT
  * path：lib/Kconfig.debug
  * 功能说明：  
    在启动早期通过 FireWire 进行远程调试。如果要调试在启动早期挂起或崩溃内核的问题，并且崩溃的计算机具有FireWire 端口，则可以使用此功能通过 FireWire 远程访问崩溃计算机的内存。它采用远程 DMA 作为 OHCI1394规范的一部分，该规范现在是 FireWire 控制器的标准。

##### 8.4 其它调试支持
* CONFIG_DEBUG_TLBFLUSH
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    TLB (Translation Lookaside Buffer)刷新操作相关的额外调试支持。TLB是一种缓存，它存储从虚拟内存地址到物理内存地址的转换，并且执行TLB刷新操作以确保TLB条目与内存映射的当前状态保持一致。这种调试支持可以帮助诊断和排除与TLB管理相关的问题，例如不正确或过时的TLB项。由于额外的调试代码，启用CONFIG_DEBUG_TLBFLUSH可能会产生一些性能开销。因此，它通常只在开发或调试阶段启用，以帮助开发人员识别和解决与tlb相关的问题。

* CONFIG_IOMMU_DEBUG
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    IOMMU调试，以帮助诊断与IOMMU使用、配置和操作相关的问题。这可能包括详细的日志记录、额外的错误检查和运行时调试功能。在遇到与IOMMU相关的问题时，启用非常有用，例如虚拟环境中的设备直通问题、DMA(直接内存访问)错误或IOMMU配置导致的内存损坏。但是，需要注意的是，启用调试选项可能会带来额外的开销，并可能影响系统性能。

* CONFIG_IO_DELAY_0X80
* CONFIG_IO_DELAY_0XED
* CONFIG_IO_DELAY_NONE
* CONFIG_IO_DELAY_UDELAY
  * path：arch/x86/Kconfig.debug
  * 功能说明：  
    端口I/O指令插入延时

* CONFIG_KGDB_LOW_LEVEL_TRAP
  * path：lib/Kconfig.kgdb
  * 功能说明：  
    KGDB (Kernel GNU Debugger)启用低级trap支持，这种机制允许KGDB捕获特定的低级事件，例如CPU异常和其他与硬件相关的事件，以提供调试功能。启用后，KGDB可以拦截和处理低级陷阱，允许开发人员检查内核状态，设置断点，并在调试会话期间逐步执行代码。这对于调试与硬件中断、异常和内核行为的其他低级方面相关的问题特别有用。
