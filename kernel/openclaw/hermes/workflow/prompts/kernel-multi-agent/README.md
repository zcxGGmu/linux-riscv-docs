# kernel-multi-agent prompts

目录说明：
- common/: 所有角色共享的系统约束与输出模板
- claude-code/: 适合 Claude Code 承担的探索、规划、审查、失败归因角色
- codex/: 适合 Codex 承担的实现、修复角色

当前拆分的是可运行 MVP 角色集：
1. Scout-Code
2. Scout-History
3. Planner
4. Spec-Review
5. Failure-Analyzer
6. Implementer
7. Fix-Agent

推荐拼装顺序：
1. `common/system-constraints.txt`
2. 具体角色 prompt 文件
3. 当前 round 的 issue / artifact 上下文
4. `common/output-template.txt`
