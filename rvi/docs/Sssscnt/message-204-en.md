# Proposal of State Sensitive Counter (Sssscnt) Extension

- Source: https://lists.riscv.org/g/sig-datacenter/message/204?p=%2C%2C%2C20%2C0%2C0%2C0%3A%3Arelevance%2C%2Cposterid%3A7911087%2C20%2C2%2C0%2C118091000
- Original title: Proposal of State sensitive Counter(Sssscnt) Extension

## Proposer

- Name: Fengxue (Esther) Zhang, Bohua Kou
- Organization: Alibaba Damo Academy

## Introduction

"Load" is generally characterized as the percentage of time that a CPU is actually running the workload. However, this metric is fundamentally incomplete unless it is normalized for operating frequency. A CPU may be running 100% of the time, but if it is operating at only 50% of its maximum frequency, it is not actually 100% loaded. To address this, the kernel's load tracking scales the observed load by the frequency at which the CPU is running [1].

The problem is:

- Modern CPUs may not know the frequency they are actually running at, because the decision is made by the power controller (PuC) or directly by hardware.

State Sensitive Counters address this by introducing counters that reflect CPU activity state, including a CPU active cycle counter and a system active cycle counter.

## Definitions

We propose State Sensitive Counters. The extension name is `Sssscnt` (`Ss` for privileged architecture and supervisor-level extensions, and `sscnt` for state-sensitive counters). A state-sensitive counter unit is implemented in each CPU and provides counters intended for system power-management use.

The state-sensitive counter unit includes a group of 64-bit event counters:

- **CPU active cycle counter**: Counts CPU core cycles at the CPU operating frequency. It pauses during CPU idle states.
- **System active cycle counter**: Counts system-level cycles at a fixed reference frequency. It pauses during CPU idle states.
- **System cycle counter**: Counts system cycles at a fixed reference frequency and increments continuously. It can be viewed as a shadow of `mtime`.

Please refer to the Background and Objectives sections for the usage scenarios described in this document.

## Background

Dynamic voltage and frequency scaling (DVFS) is a power-management technique widely used in embedded systems and computer processors to adjust the operating clock frequency dynamically based on workload and processing requirements.

The primary motivations for DVFS include improving power efficiency, optimizing system performance, and managing thermal conditions. Lowering the frequency during idle or low-demand periods reduces power consumption, which extends battery life in mobile devices and lowers overall energy usage in larger systems. In addition, DVFS helps control system temperature by reducing power dissipation, which mitigates overheating risk and improves reliability. This technique is now a standard feature in modern processors and embedded systems [1].

Choosing an appropriate CPU frequency is therefore critical. If the frequency is set too high, the CPU consumes more power than necessary, whether it is running in a phone or in a data center. If the frequency is set too low, overall system performance suffers [2].

For modern CPU-frequency governors such as `schedutil`, accurate prediction across CPUs and across all performance states requires frequency-invariant and CPU-invariant PELT (Per Entity Load Tracking) signals.

This matters because using 50% of a CPU at 1 GHz is not equivalent to using 50% at 2 GHz, and 50% utilization on a LITTLE core is not equivalent to 50% on a big core. Architectures therefore scale the time delta using two ratios: a DVFS ratio and a microarchitecture ratio.

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde5220dff77eff77c799399f43ed1ddf27f75b8339e1c4c2483d08509556868857aa156a98577f418d56ae1d5eeba82c21ed8ccd372804c0a102a3e6ca42731151b66db7f35d17d81cf6883e47f3058b297?tmpCode=2f34769f-3844-4ee7-ac58-5cd78402aa31)

For simple DVFS architectures, where software is fully in control, the ratio can be computed as:

```text
          f_cur
r_dvfs := -----
          f_max
```

For more dynamic systems, where hardware controls DVFS, hardware counters such as Intel APERF/MPERF and ARMv8.4-AMU can be used to provide the ratio. For Intel specifically:

```text
         APERF
f_cur := ----- * P0
         MPERF

           4C-turbo;  if available and turbo enabled
f_max := { 1C-turbo;  if turbo enabled
           P0;        otherwise

                  f_cur
r_dvfs := min( 1, ----- )
                  f_max
```

As a result, the `running` and `runnable` metrics become invariant with respect to DVFS level and CPU type. In other words, they can be compared and transferred across CPUs [3].

Real-time visibility into the CPU's actual operating frequency is therefore essential. In modern SoCs, however, application-processor (AP) cores usually have only request authority over frequency selection. The hardware power controller (PuC) determines the final frequency based on thermal, power, and policy constraints, and the AP often cannot read that result directly. To obtain the applied frequency, the AP must issue an explicit query through mechanisms such as a mailbox, SMC, or register polling, which introduces latency, software overhead, and the risk of stale data. Although this architectural split is important for robust hardware-enforced power management, it directly complicates DVFS accuracy and requires latency-aware algorithms.

## Objectives

Our objective is to provide low-latency, stale-free visibility into the CPU's hardware-enforced operating frequency for the application processor (AP) core. In effect, the goal is to turn frequency access from an expensive synchronous query into a near-instantaneous read capability. This preserves the PuC's control authority while giving DVFS algorithms timely data for accurate load scaling and responsive governor decisions.

1. The processor's running frequency is calculated using the following equation:

![](https://lists.riscv.org/g/sig-datacenter/attachment/204/0)

2. The processor's normalized utilization is calculated using the following equation:

![](https://lists.riscv.org/g/sig-datacenter/attachment/204/1)

These values can be obtained through the architecture-defined `arch_scale_cpu_capacity()` callback.

## Why Existing Extensions Are Insufficient

### There is no cycle counter that varies with CPU state

The existing standard `time` and `cycle` counters increment continuously regardless of whether the CPU is actively executing or is in a WFI (Wait For Interrupt) idle state.

`instret` counts instructions rather than cycles, so it is not suitable as a metric for power management or time-based load calculation.

### Why not `Zihpm`?

- **Privilege**: `Zihpm` counters are often visible only in M-mode, or require complex delegation through `mcounteren` to be visible in S-mode. Power management often needs direct S-mode visibility without heavy M-mode trapping.
- **Complexity**: `Zihpm` requires configuration, such as programming `mhpmevent`. `sscnt` instead proposes fixed-function CSRs that are always available. For a frequently running power-management loop, reducing configuration overhead is valuable.
- **Resource contention and isolation**: HPM counter resources under `Zihpm` are typically limited and shared. They are often already occupied by profiling tools such as `perf`. If the power-management driver also relies on them, resource conflicts arise.

## References

- [1] https://www.sciencedirect.com/topics/computer-science/dynamic-voltage-and-frequency-scaling
- [2] https://lwn.net/Articles/816388/
- [3] https://docs.kernel.org/scheduler/schedutil.html

Cheers,  
Fengxue
