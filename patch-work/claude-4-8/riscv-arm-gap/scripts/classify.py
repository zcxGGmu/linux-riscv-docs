#!/usr/bin/env python3
"""阶段1: 对 linux-arm-kernel 的 all_patches.jsonl 分类、按 series 去重、打标签。

与 KVM 任务不同, linux-arm-kernel 覆盖整个 ARM/ARM64 架构, 且 ~85% 是对 RISC-V
而言的"硬件噪声"(DTS/SoC 驱动/defconfig/pull-request/无关 CC)。分类法因此重写为:
  - 噪声桶 (kind=noise): 分类器批量吸收, 后续批量判 N-A, 不送子代理。
  - 信号桶 (kind=signal): arch 核心子系统, 送子代理做四态判定。

规则按优先级匹配: 高置信噪声(pull/dts/defconfig) → arch 核心信号(mm/cpufeature/...) →
广谱噪声(soc-driver/unrelated-cc/firmware) → catch-all(misc-arch / generic-cross)。

产出:
  data/arm_series.csv          去重后逻辑系列索引 (每行一系列)
  data/category_counts.md      统计概览
  data/by_category/<cat>.jsonl 按类别分组 (供阶段2子代理输入)
"""
import csv
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "data"))
IN = os.path.join(DATA, "all_patches.jsonl")

# ---------------------------------------------------------------------------
# arch 归属 (informational + 用于 generic-cross 再标注)
#   arm     —— arm64/aarch64/ARM: 前缀或 arm 专有硬件/ISA 术语
#   generic —— 无 arch 前缀的通用子系统改动 (跨架构, 多 PORTABLE)
#   other   —— 明确属其他架构 (在本列表罕见)
# ---------------------------------------------------------------------------
ARM = re.compile(
    r"\b(arm64|aarch64|gicv?[0-9]|vgic|arm-smmu|smmu|\bpsci\b|smccc|sysreg|cpucaps|"
    r"\bsve\b|\bsme\b|\bmte\b|\bpac\b|\bbti\b|\bgcs\b|midr|id_aa64|\bel[012]\b|"
    r"kvm/arm|arm_pmu|pmuv3|fpsimd|kpti|\btbi\b)", re.I)
ARM_PREFIX = re.compile(r"(^|\])\s*arm(64)?\s*:", re.I)
OTHER = re.compile(r"\b(s390|powerpc|ppc64|loongarch|\bmips\b|\bx86\b|\briscv\b)", re.I)


def classify_arch(text):
    t = text or ""
    if ARM.search(t) or ARM_PREFIX.search(t):
        return "arm"
    if OTHER.search(t):
        return "other"
    return "generic"


# ---------------------------------------------------------------------------
# 特性类别 (category, tier, kind, regex)。按优先级匹配, 第一个命中即定类。
#   tier: A=通用层  B=arch 模式可移植  C=硬件/低可移植  -=非特性单元
#   kind: noise=批量判 N-A 不送代理   signal=送子代理判定
# ---------------------------------------------------------------------------
CATEGORY_RULES = [
    # --- 高置信噪声 (最先吸收) ---
    ("pull-request", "-", "noise", re.compile(r"\[git[,\s]*pull\]|\[pull\]|\bpull request\b|\bgit pull\b", re.I)),
    ("dts-board", "C", "noise", re.compile(r"\bdts\b|\bdtsi\b|\bdtso\b|dt-bindings?|devicetree|device tree|\bdtbs?\b|\bof:|overlay to board", re.I)),
    ("defconfig", "C", "noise", re.compile(r"\bdefconfig\b", re.I)),

    # --- arch 核心信号 (先于广谱噪声, 保护 "arm64: mm:" 之类不被驱动网吞掉) ---
    ("mm-pgtable", "B", "signal", re.compile(
        r"\b(mm:|mm/|pgtable|page table|page-table|hugetlb|hugepage|huge page|\bthp\b|"
        r"transparent huge|cont-?pte|contpte|vmemmap|ioremap|\btlb\b|\btlbi\b|rodata|"
        r"\bbbml|block mapping|\bmmu\b|set_memory|linear map|linear-map|vmalloc|memblock|"
        r"page fault|\bpte\b|\bpmd\b|\bpud\b|\bp4d\b|walk_page|pagewalk|mmap|memory hotplug|"
        r"\bkasan\b|\bkfence\b|\bkmsan\b|\bkcsan\b|numa balancing|mem_encrypt)", re.I)),
    ("cpufeature-alt", "B", "signal", re.compile(
        r"\b(cpufeature|cpu feature|cpucaps|\bhwcap\b|elf_hwcap|hwprobe|alternative|"
        r"\berrata\b|cpu errata|\bmidr\b|id_aa64|sysreg|system register|sys_reg|"
        r"cpu capabilit|feature detect|feature register|cpuinfo)", re.I)),
    ("perf-pmu", "B", "signal", re.compile(
        r"\b(\bpmu\b|perf event|perf:|perf/|arm_pmu|armv8 pmu|pmuv3|\bspe\b|"
        r"statistical profil|coresight|counter overflow|hw_breakpoint|hw breakpoint|"
        r"perf test|perf tool|drivers/perf)", re.I)),
    ("entry-exception", "B", "signal", re.compile(
        r"\b(entry\.s|entry:|entry-common|exception handl|syscall|el0|context track|"
        r"irqentry|do_notify_resume|ret_to_user|kernel entry|fault handl|\bptrace\b abi|"
        r"\bpt_regs\b|stack trace|stacktrace|unwind|arch_stack)", re.I)),
    ("vdso", "B", "signal", re.compile(r"\bvdso\b|vgettimeofday|clock_gettime|gettimeofday|vvar", re.I)),
    ("trace-probe", "B", "signal", re.compile(
        r"\b(ftrace|kprobe|kretprobe|uprobe|\bbpf\b|\bjit\b|jump_label|jump label|"
        r"static key|static call|\bkgdb\b|tracepoint|function graph|fgraph|"
        r"patchable-function|rethook|ebpf|trampoline)", re.I)),
    ("atomics-locking", "B", "signal", re.compile(
        r"\b(atomic|cmpxchg|\bxchg\b|\blse\b|ll_sc|ll/sc|qspinlock|spinlock|rwlock|"
        r"\bbarrier\b|memory ordering|smp_load|smp_store|smp_cond|\bfence\b|\bwfe\b|"
        r"\bwfi\b|cmpwait|percpu ops|this_cpu)", re.I)),
    ("vector-fp", "B", "signal", re.compile(
        r"\b(\bsve\b|\bsme\b|fpsimd|fp/simd|\bneon\b|scalable vector|scalable matrix|"
        r"za state|streaming mode|kernel-mode neon|kernel mode neon|\bsimd\b|"
        r"vector length|vector regist|fp state|fpstate)", re.I)),
    ("security-hw", "B", "signal", re.compile(
        r"\b(\bmte\b|memory tag|tag-based|tagged memory|\bbti\b|branch target|\bpac\b|"
        r"pointer auth|ptrauth|\bgcs\b|guarded control|shadow stack|shadow call|\bscs\b|"
        r"\bcfi\b|control-flow|control flow integrit|\btbi\b|tagged addr|pointer mask|"
        r"\bkaslr\b|randomize_?kstack|randomize base|stack protector|hardening|"
        r"\bkpti\b|meltdown|spectre|kcfi)", re.I)),
    ("signal-ptrace-elf", "B", "signal", re.compile(
        r"\b(signal handl|sigreturn|sigframe|rt_sigreturn|\bptrace\b|\bregset\b|"
        r"\belf\b|coredump|core dump|compat_|prctl|thread_struct|tls\b|"
        r"set_thread_area|process creation|copy_thread)", re.I)),
    ("kexec-crash", "B", "signal", re.compile(
        r"\b(kexec|kdump|crash dump|crashdump|crash kernel|crashkernel|purgatory|"
        r"vmcore|kexec_file|kho\b|kernel hand)", re.I)),
    ("acpi-arch", "B", "signal", re.compile(
        r"\b(\bacpi\b|\bgicc\b|\bmadt\b|\biort\b|\brhct\b|\bapei\b|\bghes\b|\bffh\b|"
        r"cppc|\bpptt\b|\bslit\b|\bsrat\b)", re.I)),
    ("boot-head", "B", "signal", re.compile(
        r"\b(head\.s|efi stub|efi-stub|\bzboot\b|relocat|early boot|cpu bring|"
        r"smp boot|smpboot|secondary cpu|image header|boot protocol|decompress|"
        r"\bkaslr\b seed|idmap|early mapping|early_ioremap)", re.I)),
    ("irqchip", "C", "signal", re.compile(
        r"\b(gic\b|gicv?[0-9]|gic-v[0-9]|\bits\b|vgic|irqchip|irq chip|\blpi\b|"
        r"mbigen|interrupt controller|msi controller|irq domain|irqdomain|"
        r"aic\b|gpio.*irq)", re.I)),

    # --- 文档/工具 (通用, 送代理但多 PORTABLE) ---
    ("docs-tooling", "A", "signal", re.compile(
        r"\b(document|\bdocs?:|\.rst\b|selftest|kselftest|\bkunit\b|tools:|tools/|"
        r"maintainers|coccinelle|\bkconfig\b clean|checkpatch)", re.I)),

    # --- 广谱噪声 (SoC/厂商驱动 / 无关 CC / 固件 ABI) ---
    ("firmware-abi", "C", "noise", re.compile(
        r"\b(scmi|scpi|\bpsci\b|smccc|\bff-a\b|\bffa\b|arm_ffa|op-tee|optee|\btee\b|"
        r"trusted firmware|\btf-a\b|secure monitor|\bsmc\b call|firmware:|arm_scmi)", re.I)),
    ("unrelated-cc", "C", "noise", re.compile(
        r"\b(net:|netdev|net-next|ipv[46]|\btcp\b|\budp\b|ethernet|wifi|mac80211|"
        r"media:|\bfs:|ext4|btrfs|\bxfs\b|f2fs|\bscsi\b|block:|\bnvme\b|"
        r"selinux|apparmor|\bkvm:\b|virtio|vfio|vhost|rdma|infiniband)", re.I)),
    ("soc-driver", "C", "noise", re.compile(
        r"\b(clk:|clocksource:|clk-|pinctrl|\bgpio\b|soc:|reset:|\bphy:|regulator|"
        r"thermal|cpufreq|mailbox|dmaengine|\bdma:|\bi2c:|\bspi:|\bmmc:|memory:|"
        r"memory controller|watchdog|\brtc:|\bpwm:|nvmem|hwmon|\biio:|serial:|"
        r"tty:|\bmtd:|\bmfd:|power:|power supply|\bleds:|backlight|drm:|drm/|panel|"
        r"display:|\bbus:|interconnect|cpuidle|\bopp:|pmdomain|genpd|\bsram\b|"
        r"remoteproc|\biommu:|iommu/|soundwire|\basoc:|\bcodec\b|\binput:|touchscreen|"
        r"\bhwspinlock\b|\bufs:|\bcrypto:|\bspmi\b|\bmux:|extcon|\bpci:|\bpcie\b|"
        r"\bfpga\b|\bcan:|\bnfc:|\bw1:|\bhsi:|counter:|\bmisc:)", re.I)),
]


def classify_category(text):
    t = text or ""
    for cat, tier, kind, rx in CATEGORY_RULES:
        if rx.search(t):
            return cat, tier, kind
    return "misc-arch", "B", "signal"  # catch-all → 送代理三分类


# ---------------------------------------------------------------------------
# series 归一化 (去版本/编号/标签前缀) —— 复用 KVM 任务逻辑
# ---------------------------------------------------------------------------
def norm_name(name):
    if not name:
        return ""
    s = name
    s = re.sub(r"^\s*\[[^\]]*\]\s*", "", s)          # 去开头 [PATCH v3 12/34]
    s = re.sub(r"\bv\d+\b", "", s, flags=re.I)        # 去 v2/v3
    s = re.sub(r"\b\d+/\d+\b", "", s)                 # 去 12/34
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def main():
    patches = []
    seen_ids = set()
    dup = 0
    with open(IN) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = json.loads(line)
            pid = p.get("id")
            if pid is not None and pid in seen_ids:
                dup += 1  # 并发/续抓边界可能重复同一页, 按 patch id 去重
                continue
            if pid is not None:
                seen_ids.add(pid)
            patches.append(p)
    print(f"读入 {len(patches)} 条补丁 (去除重复 id {dup} 条)")

    # --- 按 series_id 分组 (无 series 的按自身 id 独立成组) ---
    groups = defaultdict(list)
    for p in patches:
        key = ("s", p["series_id"]) if p.get("series_id") else ("p", p["id"])
        groups[key].append(p)

    versions = []
    for key, members in groups.items():
        names = [m.get("name") or "" for m in members]
        sname = members[0].get("series_name") or (names[0] if names else "")
        dates = [m.get("date") for m in members if m.get("date")]
        states = sorted({m.get("state") for m in members if m.get("state")})
        rep = min(members, key=lambda m: len(m.get("name") or "~"))
        versions.append({
            "series_name": sname,
            "version": members[0].get("series_version") or 1,
            "date_max": max(dates) if dates else "",
            "date_min": min(dates) if dates else "",
            "n_patches": len(members),
            "states": states,
            "web_url": rep.get("web_url"),
            "mbox": rep.get("mbox"),
            "member_names": names,
            "norm": norm_name(sname),
        })

    # --- 按归一化名去重, 保留最新版本 (version 优先, date 兜底) ---
    logical = {}
    for v in versions:
        k = v["norm"] or v["web_url"]
        cur = logical.get(k)
        if cur is None or (v["version"], v["date_max"]) > (cur["version"], cur["date_max"]):
            v = dict(v)
            v["n_versions"] = (cur["n_versions"] + 1) if cur else 1
            v["all_states"] = sorted(set(v["states"]) | set(cur["all_states"])) if cur else v["states"]
            logical[k] = v
        else:
            cur["n_versions"] = cur.get("n_versions", 1) + 1
            cur["all_states"] = sorted(set(cur.get("all_states", cur["states"])) | set(v["states"]))

    series = list(logical.values())
    print(f"去重: {len(versions)} 个 series 版本 -> {len(series)} 个逻辑系列")

    # --- 分类 ---
    for s in series:
        text = s["series_name"] + " " + " ".join(s["member_names"][:8])
        s["arch"] = classify_arch(text)
        s["category"], s["tier"], s["kind"] = classify_category(text)
        # generic 架构且落入 misc catch-all → 归为 generic-cross (跨架构, 多 PORTABLE)
        if s["category"] == "misc-arch" and s["arch"] == "generic":
            s["category"], s["tier"] = "generic-cross", "A"

    # --- 统计 ---
    arch_ct = defaultdict(int)
    cat_ct = defaultdict(int)
    kind_ct = defaultdict(int)
    tier_ct = defaultdict(int)
    cat_meta = {}
    for s in series:
        arch_ct[s["arch"]] += 1
        cat_ct[s["category"]] += 1
        kind_ct[s["kind"]] += 1
        tier_ct[s["tier"]] += 1
        cat_meta[s["category"]] = (s["tier"], s["kind"])

    # --- 写 CSV (全部逻辑系列) ---
    series.sort(key=lambda s: (s["kind"], s["tier"], s["category"], s["date_max"]))
    csv_path = os.path.join(DATA, "arm_series.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kind", "tier", "category", "arch", "state", "date", "n_patches",
                    "n_versions", "series_name", "web_url"])
        for s in series:
            w.writerow([s["kind"], s["tier"], s["category"], s["arch"],
                        ",".join(s.get("all_states", s["states"]))[:40],
                        s["date_max"][:10], s["n_patches"], s.get("n_versions", 1),
                        s["series_name"][:120], s["web_url"]])
    print(f"写出 {csv_path} ({len(series)} 系列)")

    # --- 按类别分 JSONL (仅 signal 桶供阶段2; noise 桶也落盘供抽样) ---
    bycat_dir = os.path.join(DATA, "by_category")
    os.makedirs(bycat_dir, exist_ok=True)
    bycat = defaultdict(list)
    for s in series:
        bycat[s["category"]].append(s)
    for cat, items in bycat.items():
        items.sort(key=lambda s: s["date_max"], reverse=True)
        with open(os.path.join(bycat_dir, f"{cat}.jsonl"), "w") as f:
            for s in items:
                f.write(json.dumps({
                    "tier": s["tier"], "category": s["category"], "arch": s["arch"],
                    "kind": s["kind"], "state": s.get("all_states", s["states"]),
                    "date": s["date_max"][:10], "n_patches": s["n_patches"],
                    "series_name": s["series_name"], "web_url": s["web_url"],
                    "mbox": s["mbox"], "sample_titles": s["member_names"][:6],
                }, ensure_ascii=False) + "\n")

    # --- 写统计 md ---
    n_signal = kind_ct.get("signal", 0)
    n_noise = kind_ct.get("noise", 0)
    md = ["# 分类统计概览 (linux-arm-kernel → RISC-V)\n",
          f"- 原始补丁: **{len(patches)}**",
          f"- series 版本: **{len(versions)}** → 去重逻辑系列: **{len(series)}**",
          f"- 信号系列 (送子代理): **{n_signal}** · 噪声系列 (批量 N-A): **{n_noise}** "
          f"(信号占比 {100*n_signal/max(1,len(series)):.1f}%)\n",
          "## 架构归属分布\n", "| arch | 系列数 |", "|---|---|"]
    for k, v in sorted(arch_ct.items(), key=lambda kv: -kv[1]):
        md.append(f"| {k} | {v} |")
    md.append("\n## 类别分布 (含层级/kind)\n| kind | 层级 | 类别 | 系列数 |\n|---|---|---|---|")
    for cat, n in sorted(cat_ct.items(), key=lambda kv: (cat_meta[kv[0]][1], -kv[1])):
        tier, kind = cat_meta[cat]
        md.append(f"| {kind} | {tier} | {cat} | {n} |")
    with open(os.path.join(DATA, "category_counts.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("写出 category_counts.md")
    print(f"\n信号桶 (送阶段2子代理), 共 {n_signal} 系列:")
    for cat in sorted(bycat):
        tier, kind = cat_meta[cat]
        if kind == "signal":
            print(f"  [{tier}] {cat}: {len(bycat[cat])}")
    print(f"\n噪声桶 (批量 N-A), 共 {n_noise} 系列:")
    for cat in sorted(bycat):
        tier, kind = cat_meta[cat]
        if kind == "noise":
            print(f"  {cat}: {len(bycat[cat])}")


if __name__ == "__main__":
    main()
