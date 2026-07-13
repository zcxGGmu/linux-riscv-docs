#!/usr/bin/env python3
"""阶段1: 对 all_patches.jsonl 分类、按 series 去重、打标签。

产出:
  data/x86_arm_series.csv    去重后的 x86/arm 逻辑系列索引 (每行一系列)
  data/category_counts.md    统计概览
  data/by_category/<cat>.jsonl  按类别分组 (供阶段2子代理输入)
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
# 架构分类 (优先级顺序; 词边界避免 its/arm 等误判)
# ---------------------------------------------------------------------------
RISCV = re.compile(r"\b(risc-?v|kvm/riscv|aia|imsic|aplic)\b", re.I)
OTHER = re.compile(r"\b(s390|powerpc|ppc64|book3s|loongarch|\bmips\b)\b", re.I)
X86 = re.compile(
    r"\b(x86|vmx|svm|nvmx|nsvm|vmcs|vmcb|sev|sev-es|sev-snp|\bsnp\b|tdx|sgx|"
    r"lapic|ioapic|apicv|avic|xen|hyper-?v|hyperv|mtrr|\bsmm\b|vmenter|vmexit|"
    r"kvmclock|xsave|xstate|cpuid|\bmsr\b|pdpte|\bpat\b|\bpit\b|nested vmx)\b", re.I)
ARM = re.compile(
    r"\b(arm64|aarch64|vgic|gicv[0-9]|gic-v[0-9]|vgic-its|pkvm|nvhe|\bvhe\b|"
    r"pauth|sysreg|sys_reg|smccc|\bpsci\b|arm_smmu|el2|cptr|\bcca\b|\brme\b|"
    r"realm|feat_)\b", re.I)
ARM_PREFIX = re.compile(r"kvm:\s*arm", re.I)
X86_PREFIX = re.compile(r"kvm:\s*(x86|vmx|svm|nvmx|nsvm|sev|tdx|sgx)", re.I)
TEST = re.compile(r"\b(selftest|selftests|kvm-unit-test|kunit)\b", re.I)
DOC = re.compile(r"\b(documentation|docs?:)\b", re.I)


def classify_arch(text):
    t = text or ""
    is_x86 = bool(X86.search(t) or X86_PREFIX.search(t))
    is_arm = bool(ARM.search(t) or ARM_PREFIX.search(t))
    if RISCV.search(t) and not (is_x86 or is_arm):
        return "riscv"
    if OTHER.search(t) and not (is_x86 or is_arm):
        return "other"
    if is_x86 and is_arm:
        return "x86+arm"
    if is_x86:
        return "x86"
    if is_arm:
        return "arm"
    return "common"


# ---------------------------------------------------------------------------
# 特性类别 (映射到 20 类 / 3 层级)。规则按优先级匹配。
# ---------------------------------------------------------------------------
CATEGORY_RULES = [
    # (category, tier, regex) —— 按优先级匹配，第一个命中即定类
    # 先滤除非特性单元 (pull request 汇总 / 独立测试套件 / 纯构建维护)
    ("pull-request", "-", re.compile(r"\[git[,\s]*pull\]|\[pull\]|\bpull request\b", re.I)),
    ("kvm-unit-tests", "T", re.compile(r"\[kvm-unit-tests?\]", re.I)),
    ("confidential", "C", re.compile(r"\b(tdx|sev|sev-es|sev-snp|\bsnp\b|pkvm|\bcca\b|\brme\b|realm|coco|private mem|gmem attribut|secure)\b", re.I)),
    ("nested", "C", re.compile(r"\b(nested|nvmx|nsvm|vmcs12|shadow vmcs|nv2|nested virt|l2 guest)\b", re.I)),
    ("vendor-enlighten", "C", re.compile(r"\b(hyper-?v|hyperv|\bxen\b|evmcs|enlighten)\b", re.I)),
    ("x86-legacy", "C", re.compile(r"\b(\bsmm\b|mtrr|\bpit\b|i8254|i8259|\bpic\b|\bsgx\b|real mode|vm86)\b", re.I)),
    ("hw-virt-engine", "C", re.compile(r"\b(vmenter|vmexit|world switch|vmrun|vmload|vmsave|__vmx|nvhe|\bvhe\b|hyp entry|hyp switch)\b", re.I)),
    ("irqchip-hw", "C", re.compile(r"\b(lapic|ioapic|apicv|avic|posted[- ]?int|vgic|gic-v[0-9]|gicv[0-9]|vgic-its|\bits\b|lpi|\birq controller\b)\b", re.I)),
    ("guest_memfd", "A", re.compile(r"\b(guest_memfd|gmem|memfd|memory attribute|KVM_CREATE_GUEST_MEMFD|private memory|shared memory conversion)\b", re.I)),
    ("dirty-ring", "A", re.compile(r"\bdirty[- ]?ring\b", re.I)),
    ("io-irq-infra", "A", re.compile(r"\b(irqfd|ioeventfd|coalesced|eventfd|irq routing|irq bypass|gsi routing|msi routing)\b", re.I)),
    ("stats", "A", re.compile(r"\b(binary stat|debugfs stat|vcpu stat|vm stat|statistics)\b", re.I)),
    ("mmu-stage2", "B", re.compile(r"\b(tdp_mmu|tdp mmu|stage[- ]?2|stage2|gstage|g-stage|page[- ]?table|hugepage|huge page|page split|eager split|dirty log|write.?protect|nx_huge|shadow page|spte|rmap|mmu)\b", re.I)),
    ("reg-access", "B", re.compile(r"\b(one_?reg|sys_?reg|sysreg|cpuid|id[- ]?reg|get-reg-list|reg-list|feature reg|msr filter|vcpu attribute)\b", re.I)),
    ("pmu", "B", re.compile(r"\bpmu|perf event|counter|pmc|event filter|pmc\b", re.I)),
    ("timer-clock", "B", re.compile(r"\b(timer|kvmclock|\btsc\b|clocksource|arch_timer|ptp|steal[- ]?time|stimer)\b", re.I)),
    ("pv-hypercall", "B", re.compile(r"\b(hypercall|paravirt|pv[- ]|async_?pf|async page fault|psci|smccc|pvclock|pv-time|pvtime|pv spinlock|pv tlb)\b", re.I)),
    ("mmio-insn", "B", re.compile(r"\b(mmio|instruction|emulat|decode|insn|opcode)\b", re.I)),
    ("debug-introspect", "B", re.compile(r"\b(ptdump|debugfs|guest debug|breakpoint|watchpoint|single[- ]?step|introspect|tracepoint|trace event)\b", re.I)),
    ("selftests", "B", re.compile(r"\b(selftest|selftests|kvm-unit-test)\b", re.I)),
    ("docs", "A", re.compile(r"\b(documentation|docs?:)\b", re.I)),
    ("core", "A", re.compile(r"\b(kvm_main|ioctl|KVM_CAP|enable_cap|capabilit|vcpu run|kvm_run|vm lifecycle|create vm|destroy vm|memslot|mmu_notifier)\b", re.I)),
    # 低优先级 catch-all: x86 状态/基础设施维护 (多为 Tier-C 不可移植)
    ("fpu-xstate", "C", re.compile(r"\b(xsave|xstate|fxsave|fpstate|\bfpu\b|pkru|\bpks\b)\b", re.I)),
    ("arch-infra", "C", re.compile(r"\b(kvm_x86_call|kvm_x86_ops|static_call|kvm-asm|read_mostly|module param|kbuild|makefile|kconfig|__exit attribute)\b", re.I)),
]


def classify_category(text):
    t = text or ""
    for cat, tier, rx in CATEGORY_RULES:
        if rx.search(t):
            return cat, tier
    return "misc", "?"


# ---------------------------------------------------------------------------
# series 归一化 (去版本/编号/标签前缀)
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
    with open(IN) as f:
        for line in f:
            line = line.strip()
            if line:
                patches.append(json.loads(line))
    print(f"读入 {len(patches)} 条补丁")

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
        # 代表 url: 取最短 name (通常是 cover 或 1/N) 的 web_url
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
        s["category"], s["tier"] = classify_category(text)
        s["is_test"] = bool(TEST.search(text))

    # --- 统计 ---
    arch_ct = defaultdict(int)
    cat_ct = defaultdict(int)
    tier_ct = defaultdict(int)
    xa_cat = defaultdict(int)
    for s in series:
        arch_ct[s["arch"]] += 1
    x86_arm = [s for s in series if s["arch"] in ("x86", "arm", "x86+arm")]
    for s in x86_arm:
        cat_ct[s["category"]] += 1
        tier_ct[s["tier"]] += 1
        xa_cat[(s["tier"], s["category"])] += 1

    # --- 写 CSV ---
    x86_arm.sort(key=lambda s: (s["tier"], s["category"], s["date_max"]))
    csv_path = os.path.join(DATA, "x86_arm_series.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tier", "category", "arch", "state", "date", "n_patches",
                    "n_versions", "series_name", "web_url"])
        for s in x86_arm:
            w.writerow([s["tier"], s["category"], s["arch"],
                        ",".join(s.get("all_states", s["states"]))[:40],
                        s["date_max"][:10], s["n_patches"], s.get("n_versions", 1),
                        s["series_name"][:120], s["web_url"]])
    print(f"写出 {csv_path} ({len(x86_arm)} 系列)")

    # --- 按类别分 JSONL (供阶段2) ---
    bycat_dir = os.path.join(DATA, "by_category")
    os.makedirs(bycat_dir, exist_ok=True)
    bycat = defaultdict(list)
    for s in x86_arm:
        bycat[f"{s['tier']}_{s['category']}"].append(s)
    for cat, items in bycat.items():
        with open(os.path.join(bycat_dir, f"{cat}.jsonl"), "w") as f:
            for s in items:
                f.write(json.dumps({
                    "tier": s["tier"], "category": s["category"], "arch": s["arch"],
                    "state": s.get("all_states", s["states"]), "date": s["date_max"][:10],
                    "n_patches": s["n_patches"], "series_name": s["series_name"],
                    "web_url": s["web_url"], "mbox": s["mbox"],
                    "sample_titles": s["member_names"][:6],
                }, ensure_ascii=False) + "\n")

    # --- 写统计 md ---
    md = ["# 分类统计概览\n",
          f"- 原始补丁: **{len(patches)}**",
          f"- series 版本: **{len(versions)}** → 去重逻辑系列: **{len(series)}**",
          f"- 其中 x86/arm 系列: **{len(x86_arm)}**\n",
          "## 全体系列架构分布\n", "| 架构 | 系列数 |", "|---|---|"]
    for k, v in sorted(arch_ct.items(), key=lambda kv: -kv[1]):
        md.append(f"| {k} | {v} |")
    md.append("\n## x86/arm 系列 · 层级分布\n| 层级 | 系列数 |\n|---|---|")
    for k in ("A", "B", "C", "?"):
        if tier_ct.get(k):
            md.append(f"| {k} | {tier_ct[k]} |")
    md.append("\n## x86/arm 系列 · 类别分布 (含层级)\n| 层级 | 类别 | 系列数 |\n|---|---|---|")
    for (tier, cat), n in sorted(xa_cat.items(), key=lambda kv: (kv[0][0], -kv[1])):
        md.append(f"| {tier} | {cat} | {n} |")
    with open(os.path.join(DATA, "category_counts.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("写出 category_counts.md")
    print("\n各类别文件 (供阶段2):")
    for cat in sorted(bycat):
        print(f"  {cat}: {len(bycat[cat])}")


if __name__ == "__main__":
    main()
