# 内核多智能体工作流工件目录模板

建议每个 issue 使用一个独立目录：

```text
artifacts/<issue-id>/
├── discover/
│   ├── code-evidence.md
│   └── history-evidence.md
├── plans/
│   ├── design.md
│   ├── test-matrix.md
│   └── risk.md
├── review/
│   ├── spec-round-1.md
│   └── upstream-round-1.md
├── debug/
│   ├── failure-analysis-round-1.md
│   ├── fix-summary-round-1.md
│   └── regression-round-1.md
├── patch/
│   ├── series-cover-letter.md
│   ├── checkpatch.txt
│   ├── get-maintainer.txt
│   └── send-email-example.sh
├── logs/
│   ├── build-round-1.log
│   └── test-round-1.log
└── state/
    ├── workflow.yaml
    ├── issue-brief.md
    ├── keywords.txt
    ├── subsystem-paths.txt
    ├── gap_registry.yaml
    ├── issue_map.yaml
    └── change-summary-round-1.md
```

最小要求：
- 每个阶段必须有落盘工件
- review/debug 产物必须带 round 编号
- 所有 agent 通过 `state/workflow.yaml` 回写状态
- 人工 Gate 结果也必须写回 `state/workflow.yaml`
