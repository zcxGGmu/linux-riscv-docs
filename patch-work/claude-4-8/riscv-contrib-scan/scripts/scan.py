#!/usr/bin/env python3
"""扫描本地内核树, 挖掘 RISC-V 贡献点候选 (三路信号, 全部只读):

  1. Documentation/features/**/arch-support.txt 中 riscv 标 TODO 的特性 (官方维护矩阵)
  2. arm64 / x86 select 了、而 riscv 未 select 的 Kconfig 能力符号 (差集)
  3. arch/riscv 及 riscv 相关驱动中的 TODO/FIXME/桩标记

输出 Markdown 报告到 stdout (调用方重定向到 README.md)。
"""
import os
import re
import sys
import glob
from collections import defaultdict

SRC = os.environ.get("SRC", "/Users/zq/Desktop/patch-work/linux-riscv")


# ---------------------------------------------------------------------------
# 扫描 1: Documentation/features 架构支持矩阵中 riscv = TODO
# ---------------------------------------------------------------------------
def scan_features():
    rows = []
    for f in sorted(glob.glob(os.path.join(SRC, "Documentation/features/**/arch-support.txt"), recursive=True)):
        txt = open(f, encoding="utf-8", errors="replace").read()
        m_status = re.search(r"\|\s*riscv:\s*\|\s*(\w+)\s*\|", txt)
        if not m_status:
            continue
        status = m_status.group(1)
        name = (re.search(r"#\s*Feature name:\s*(.+)", txt) or [None, "?"])[1].strip()
        kcfg = (re.search(r"#\s*Kconfig:\s*(.+)", txt) or [None, "-"])[1].strip()
        desc = (re.search(r"#\s*description:\s*(.+)", txt) or [None, ""])[1].strip()
        subsys = os.path.relpath(os.path.dirname(f), os.path.join(SRC, "Documentation/features")).split(os.sep)[0]
        rows.append({"subsys": subsys, "name": name, "kcfg": kcfg, "desc": desc, "status": status})
    todo = [r for r in rows if r["status"].upper() == "TODO"]
    return rows, todo


# ---------------------------------------------------------------------------
# 扫描 2: Kconfig select 差集 (arm64 ∪ x86) − riscv
# ---------------------------------------------------------------------------
SELECT_RE = re.compile(r"^\s*select\s+([A-Z0-9_]+)")
# 过滤明显架构内部/平台/CPU 命名 (非通用能力), 降噪
NOISE_PREFIX = re.compile(r"^(ARM64|ARM|X86|CPU_SUP|MICROCODE|INTEL|AMD|XEN|PVH|"
                          r"HYPERV|CRYPTO_|PINCTRL|GPIO|MFD|COMMON_CLK|PCOWER|"
                          r"SND_|MTD|SERIAL_|I2C_|SPI_|MMC|USB|PCI_|OF_)")


def arch_selects(arch):
    got = set()
    for kf in glob.glob(os.path.join(SRC, f"arch/{arch}/Kconfig*")):
        for line in open(kf, encoding="utf-8", errors="replace"):
            m = SELECT_RE.match(line)
            if m:
                got.add(m.group(1))
    return got


def scan_kconfig():
    a64, x86, rv = arch_selects("arm64"), arch_selects("x86"), arch_selects("riscv")
    both = sorted((a64 & x86) - rv)
    either = sorted((a64 | x86) - rv - set(both))

    def keep(sym):
        return not NOISE_PREFIX.match(sym)

    both_cap = [s for s in both if keep(s)]
    either_cap = [s for s in either if keep(s)]

    def annotate(sym):
        who = []
        if sym in a64:
            who.append("arm64")
        if sym in x86:
            who.append("x86")
        return "+".join(who)

    return both_cap, either_cap, annotate, len(a64), len(x86), len(rv)


# ---------------------------------------------------------------------------
# 扫描 3: arch/riscv 及 riscv 驱动的 TODO/FIXME/桩
# ---------------------------------------------------------------------------
MARK_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
STUB_RE = re.compile(r"not (yet )?(supported|implemented)|unsupported|return -ENOSYS", re.I)
SCAN_DIRS = ["arch/riscv", "drivers/perf", "drivers/irqchip", "drivers/iommu/riscv"]
RV_HINT = re.compile(r"riscv|imsic|aplic|sbi|thead|sifive|andes", re.I)


def scan_todos():
    code, dts = [], []
    for d in SCAN_DIRS:
        base = os.path.join(SRC, d)
        for root, _, files in os.walk(base):
            for fn in files:
                if not fn.endswith((".c", ".h", ".S", ".dts", ".dtsi", ".rst", "Kconfig", "Makefile")):
                    continue
                p = os.path.join(root, fn)
                # drivers/perf|irqchip 只取 riscv 相关文件
                rel = os.path.relpath(p, SRC)
                if d in ("drivers/perf", "drivers/irqchip") and not RV_HINT.search(fn):
                    continue
                try:
                    for i, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
                        if MARK_RE.search(line) or STUB_RE.search(line):
                            entry = (rel, i, line.strip()[:110])
                            (dts if fn.endswith((".dts", ".dtsi")) else code).append(entry)
                except Exception:
                    pass
    return code, dts


# ---------------------------------------------------------------------------
# 成文
# ---------------------------------------------------------------------------
def main():
    all_feat, todo_feat = scan_features()
    both_cap, either_cap, ann, n64, nx86, nrv = scan_kconfig()
    code_todo, dts_todo = scan_todos()

    ok_feat = len(all_feat) - len(todo_feat)
    P = print
    P("# RISC-V 贡献点候选扫描 (内核源码树内信号)\n")
    P(f"> 源码树：`{SRC}`（Linux v7.2.0-rc3，只读）。由 `scripts/scan.py` 自动生成。")
    P("> 与 `../riscv-arm-gap/`（补丁邮件列表差异挖掘）**互补**：本扫描直接从内核树静态信号出发，")
    P("> 找「官方标记待办 / 架构能力差集 / 代码内 TODO」——发现的是**当前树的真实缺口**，而非在途补丁。\n")

    P("## TL;DR\n")
    P(f"- **扫描 1（官方特性矩阵）**：`Documentation/features` 共 {len(all_feat)} 项特性，"
      f"riscv 已支持 {ok_feat}、**标 TODO {len(todo_feat)} 项**（见 §1，最权威）。")
    P(f"- **扫描 2（Kconfig 能力差集）**：arm64({n64}) / x86({nx86}) / riscv({nrv}) 的 select 符号中，"
      f"**arm64∪x86 有、riscv 无**的能力类符号 {len(both_cap)+len(either_cap)} 个"
      f"（其中 arm64 与 x86 **都有**的 {len(both_cap)} 个，信号最强，见 §2）。")
    P(f"- **扫描 3（代码内 TODO/桩）**：arch/riscv 及 riscv 驱动中 {len(code_todo)} 处代码级 "
      f"TODO/FIXME/桩标记（另 {len(dts_todo)} 处 DTS 板级），见 §3。\n")
    P("> ⚠️ 扫描 2/3 为**候选**，需人工判断（部分符号可能经传递 select 获得、或对 riscv 语义上不适用）；"
      "扫描 1 是维护者标注，最可信。\n")

    # ---- §1 ----
    P("## 1. `Documentation/features` 中 riscv 标 TODO 的特性（官方矩阵，最可信）\n")
    P("| 子系统 | 特性 | Kconfig | 说明 |")
    P("|---|---|---|---|")
    for r in sorted(todo_feat, key=lambda r: (r["subsys"], r["name"])):
        P(f"| {r['subsys']} | {r['name']} | `{r['kcfg']}` | {r['desc'][:70]} |")
    P("")

    # ---- §2 ----
    P("## 2. Kconfig 能力符号差集：arm64 ∪ x86 select 而 riscv 未 select\n")
    P(f"### 2a. arm64 与 x86 **都** select（最强信号，{len(both_cap)} 个）\n")
    P("| Kconfig 符号 | 提供方 |")
    P("|---|---|")
    for s in both_cap:
        P(f"| `{s}` | {ann(s)} |")
    P(f"\n### 2b. 仅 arm64 或仅 x86 select（{len(either_cap)} 个，次强）\n")
    P("<details><summary>展开</summary>\n")
    P("| Kconfig 符号 | 提供方 |")
    P("|---|---|")
    for s in either_cap:
        P(f"| `{s}` | {ann(s)} |")
    P("\n</details>\n")

    # ---- §3 ----
    P("## 3. arch/riscv 及 riscv 驱动内的 TODO/FIXME/桩\n")
    P(f"### 3a. 代码级（{len(code_todo)} 处，优先）\n")
    P("| 文件:行 | 内容 |")
    P("|---|---|")
    pipe = "\\|"
    for rel, i, s in sorted(code_todo):
        esc = s.replace("|", pipe)
        P(f"| `{rel}:{i}` | {esc} |")
    P(f"\n### 3b. DTS/板级（{len(dts_todo)} 处，价值较低，折叠）\n")
    P("<details><summary>展开</summary>\n")
    for rel, i, s in sorted(dts_todo):
        P(f"- `{rel}:{i}` — {s}")
    P("\n</details>\n")

    # stderr 摘要
    sys.stderr.write(f"features TODO={len(todo_feat)}/{len(all_feat)}  kconfig both={len(both_cap)} "
                     f"either={len(either_cap)}  code_todo={len(code_todo)} dts_todo={len(dts_todo)}\n")


if __name__ == "__main__":
    main()
