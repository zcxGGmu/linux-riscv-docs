# 任务计划：patch-work 贡献指引 README

- [x] 复习项目 lessons（当前未发现 `tasks/lessons.md`）。
- [x] 只读盘点 `patch-work/` 下所有探索目录与文档结构。
- [x] 并行分析主要探索方向，提炼每个目录的主题、成果、适合人群和下一步贡献方式。
- [x] 在 `patch-work/README.md` 生成面向 linux-riscv 贡献开发者的明确指引，不修改既有探索目录内容。
- [x] 校验未改动探索目录内容，README 覆盖所有主要目录并链接准确。
- [x] 在本文件末尾记录 review 结果。

## Review

- 新增文件：`patch-work/README.md`。
- 覆盖目录：`claude-4-8/`、`fpsimd/`、`kvm-cfi/`、`kvm-riscv/`、`riscv-arm-x86-gap/`、`riscv-contributions-explore/`、`riscv_arm_isa/`。
- 链接校验：README 内部相对链接缺失数为 0。
- 变更边界：未修改 `patch-work/` 既有探索子目录内容；仅新增顶层 README，并更新本任务跟踪文件。

---

# 任务计划：patch-work Linux RISC-V 潜在贡献移植清单

- [x] 复习项目 lessons（当前未发现 `tasks/lessons.md`），读取 `patch-work/AGENTS.md` 与贡献点评分规则。
- [x] 全量盘点 `patch-work/` 的 188 个文件，按跨架构、KVM、FPSIMD/Vector、ISA 与通用扫描建立内容索引。
- [x] 并行提取并交叉核对候选任务、上游状态、源补丁/邮件链接、实现边界与验证路径。
- [x] 对候选去重，统一标记优先级、难易度、置信度、贡献适配度及依赖风险。
- [x] 将综合总结和可勾选待办清单写入 `patch-work/README.md`，保留详细本地证据链接。
- [x] 验证全部主要目录被覆盖、内部链接有效、外部来源格式完整且无占位符，并检查最终 diff。
- [x] 在本节末尾记录 Review 结果。

## Review

- 全量覆盖：188 个文件（131 Markdown、47 JSONL、5 Python、2 CSV、1 shell、1 PDF、1 JSON）。
- 综合产物：`patch-work/README.md` 新增统一评分、Top 5、93 个可勾选任务/方向、已覆盖项和完整次级索引。
- 关键修正：剔除已进入 common/当前树的 KVM 候选；确认 RVV ptrace/coredump/kernel Vector 已实现；将旧 FPSIMD 性能数字降为低置信研究。
- 链接验证：全部本地文件目标存在；带 fragment 的本地链接均匹配 heading 或显式 ID；代表性 git.kernel.org、Patchwork、infradead、LWN 链接返回 200。
- 外部限制：lore.kernel.org 与 patch.msgid.link 对自动请求返回 403；保留本地研究中记录的原始 URL，未据此声称在线状态已复核。
- 变更边界：仅修改 `patch-work/README.md` 和本任务跟踪段落；未修改任何原始研究、JSONL/CSV、脚本或内核源码。
