# Todo

- [x] 复习 `tasks/lessons.md`、仓库结构与上层已有文档
- [x] 使用多 Agent 并行收集仓库文档风格与工作流骨架
- [x] 设计 OpenClaw / Claude Code / Codex 的角色分工、状态流转与人工 Gate
- [x] 输出可落盘的方案文档，包含 Mermaid 图与可执行配置建议
- [x] 补充示例配置文件，覆盖仓库、Agent、阈值、命令与邮件发送参数
- [x] 校验文档完整性、引用与文件布局

## Review

- 已生成主方案文档：`docs/plans/2026-03-10-riscv-gap-multi-agent-design.md`
- 已生成示例配置：`configs/workflow.example.yaml`
- 已校验关键章节存在：`Step-1~Step-5`、`OpenClaw`、`Claude Code`、`Codex`、人工 Gate、3 个 Mermaid 图
- 已验证 YAML 可解析：`python3 -c "import yaml,sys; yaml.safe_load(open('configs/workflow.example.yaml')); print('yaml-ok')"` 输出 `yaml-ok`

## Next Batch

- [x] 写本轮实现计划：`docs/plans/2026-03-10-riscv-gap-assets-implementation.md`
- [x] 生成 issue / design Markdown 模板
- [x] 生成 Claude Planner / Codex Implementer / Codex Verifier prompt 模板
- [x] 生成 `state/` schema 与说明文档
- [x] 更新主设计文档对新资产的引用
- [x] 校验 Markdown / JSON / YAML 资产

## Review Addendum

- 已生成模板：`templates/issue-template.md`、`templates/design-template.md`
- 已生成 prompt：`prompts/claude-planner-prompt.md`、`prompts/codex-implementer-prompt.md`、`prompts/codex-verifier-prompt.md`
- 已生成 state 说明与 schema：`state/README.md`、`state/schema/*.schema.json`
- 已更新配置引用：`configs/workflow.example.yaml` 增加模板、prompt、schema 路径
- 已更新主设计文档目录与资产说明：`docs/plans/2026-03-10-riscv-gap-multi-agent-design.md`
- 已验证资产解析：`asset-validation-ok`
- `git status --short` 显示上层仓库存在非本轮改动：`../cc/`、`../openclaw_config.md` 和一个上层删除项；本轮未回滚这些改动

## Issue RV-KVM-NESTED-001 Iteration 1

- [x] 复习 `kernel/openclaw/codex/tasks/lessons.md`、`kernel/openclaw/plans/issue-1-plan.md` 与相关技能约束
- [x] 确认目标代码仓库 `/home/zq/work-space/repo/patch-work/linux` 当前状态与可写性
- [ ] 基于现有 RISC-V KVM 代码定位 nested 最小框架的结构体、生命周期与 SBI HFENCE 接口落点
- [ ] 在 `/home/zq/work-space/repo/patch-work/linux` 实现最小 nested virtualization 框架并保持可编译
- [ ] 运行至少一次相关最小化编译检查并记录结果
- [ ] 写入 `kernel/openclaw/state/run_history/issue-1-iter-1.json`
- [ ] 写入 `kernel/openclaw/logs/issue-1-iter-1.md`

## Review Pending

- 当前会话对 `/home/zq/work-space/repo/patch-work/linux` 的写入已验证失败：`touch .../.codex_write_test` 返回 `Permission denied`
- 在未解决写权限前，不应声称已完成第 1 轮代码实现；本轮先完成代码落点分析、阻塞记录与可复用的执行说明
