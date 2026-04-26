# oh-my-claw Docs Index

本页是 `oh-my-claw` 当前文档集的导航入口。

如果你是第一次进入这个仓库，请不要随机阅读所有文档。最有效的方式是按角色和目标选择阅读路径。

---

## 1. 这个仓库目前处于什么阶段

当前仓库还没有进入正式编码实现阶段，但已经完成了一整套 **MVP / Phase 1 设计前置文档**，包括：

- 项目定位与方案
- MVP 阶段拆分
- Phase 1 实施计划
- 架构设计
- Workflow 规格
- 验收标准
- 配置规格
- backlog 与 issue 草稿

因此，这个仓库当前最适合：

- 做设计评审
- 做实施前准备
- 做任务拆分与排期
- 做后续 GitHub issue / project board 初始化

---

## 2. 推荐阅读顺序

### 路径 A：第一次了解项目

如果你第一次接触 `oh-my-claw`，建议按下面顺序阅读：

1. `README.md`
2. `oh-my-claw-proposal.md`
3. `oh-my-claw-architecture.md`
4. `oh-my-claw-mvp-phases.md`

这条路径适合：

- 想快速理解项目定位的人
- 做立项评审的人
- 想知道“为什么要做这个项目”的人

### 路径 B：准备进入实现

如果你准备开始实现 MVP，建议按下面顺序阅读：

1. `README.md`
2. `oh-my-claw-mvp-implementation-plan.md`
3. `oh-my-claw-architecture.md`
4. `oh-my-claw-workflow-specs.md`
5. `oh-my-claw-config-spec.md`
6. `oh-my-claw-acceptance-test-plan.md`
7. `milestones-and-issues.md`
8. `github-issues-draft.md`

这条路径适合：

- 负责开发的人
- 负责拆分任务的人
- 负责建立 issue tracker 的人

### 路径 C：准备做评审或验收

如果你负责 review / 验收 / 方案把关，建议按下面顺序阅读：

1. `README.md`
2. `oh-my-claw-proposal.md`
3. `oh-my-claw-workflow-specs.md`
4. `oh-my-claw-acceptance-test-plan.md`
5. `oh-my-claw-config-spec.md`

这条路径适合：

- 技术负责人
- 设计评审人
- 验收标准制定者

---

## 3. 文档地图

## 3.1 项目入口

### `README.md`

用途：

- 项目入口
- 对外说明
- 当前状态摘要
- 文档导航的上层介绍

适合谁：

- 所有人

---

## 3.2 方案与定位

### `oh-my-claw-proposal.md`

用途：

- 解释为什么要做 `oh-my-claw`
- 对比 `oh-my-openagent` 与 `openclaw`
- 给出产品定位、模块划分、MVP 范围和路线图

适合谁：

- 立项者
- 设计者
- 做整体判断的人

---

## 3.3 阶段与推进策略

### `oh-my-claw-mvp-phases.md`

用途：

- 定义 MVP 分阶段推进方式
- 明确先后端还是前后端并行
- 给出阶段任务清单

适合谁：

- 负责人
- 计划制定者
- 项目管理者

---

## 3.4 实施计划

### `oh-my-claw-mvp-implementation-plan.md`

用途：

- 把 Phase 1 拆到文件级、接口级、测试级
- 规定推荐实施顺序
- 规定 Phase 1 完成定义

适合谁：

- 开发者
- 架构实现负责人

---

## 3.5 架构设计

### `oh-my-claw-architecture.md`

用途：

- 定义系统边界
- 定义主链路
- 定义模块职责、状态流、扩展点

适合谁：

- 架构设计者
- 实现负责人
- review 人员

---

## 3.6 Workflow 规格

### `oh-my-claw-workflow-specs.md`

用途：

- 定义三个 MVP workflow 的步骤、输出、失败路径
- 统一 workflow 骨架
- 约束 summary 结构

适合谁：

- workflow 实现者
- reviewer
- 测试设计者

---

## 3.7 验收标准

### `oh-my-claw-acceptance-test-plan.md`

用途：

- 定义 Phase 1 系统级验收场景
- 给出 Pass / Partial / Fail 标准
- 定义什么叫“MVP 成立”

适合谁：

- 测试设计者
- reviewer
- 技术负责人

---

## 3.8 配置规格

### `oh-my-claw-config-spec.md`

用途：

- 定义 MVP 配置边界
- 定义默认值、覆盖规则、稳定性等级、校验规则

适合谁：

- 配置系统实现者
- reviewer
- 后续文档维护者

---

## 3.9 任务管理与执行

### `milestones-and-issues.md`

用途：

- 按 milestone 拆分 backlog
- 给出 issue 粒度的实现任务和依赖关系

适合谁：

- 项目经理
- 开发负责人
- 任务拆分者

### `github-issues-draft.md`

用途：

- 把 backlog 进一步转为 GitHub issue 草稿格式
- 可直接复制到 issue tracker

适合谁：

- 仓库维护者
- issue 创建者
- project board 初始化者

---

## 4. 角色导向阅读建议

## 4.1 如果你是项目 Owner

先看：

1. `README.md`
2. `oh-my-claw-proposal.md`
3. `oh-my-claw-mvp-phases.md`
4. `milestones-and-issues.md`

## 4.2 如果你是架构/技术负责人

先看：

1. `README.md`
2. `oh-my-claw-architecture.md`
3. `oh-my-claw-workflow-specs.md`
4. `oh-my-claw-config-spec.md`
5. `oh-my-claw-acceptance-test-plan.md`

## 4.3 如果你是开发者

先看：

1. `README.md`
2. `oh-my-claw-mvp-implementation-plan.md`
3. `oh-my-claw-architecture.md`
4. `oh-my-claw-workflow-specs.md`
5. `milestones-and-issues.md`

## 4.4 如果你是测试/验收负责人

先看：

1. `README.md`
2. `oh-my-claw-workflow-specs.md`
3. `oh-my-claw-acceptance-test-plan.md`
4. `oh-my-claw-config-spec.md`

---

## 5. 当前最关键的文档组合

如果只看三份文档，我建议优先：

1. `README.md`
2. `oh-my-claw-architecture.md`
3. `oh-my-claw-mvp-implementation-plan.md`

理由：

- `README` 负责建立全局认知
- `architecture` 负责定义系统边界
- `implementation plan` 负责告诉你下一步怎么做

---

## 6. 当前仓库的推荐下一步

如果准备继续推进项目，推荐顺序是：

1. 根据 `milestones-and-issues.md` 创建真正的 issue tracker
2. 根据 `github-issues-draft.md` 批量创建 issues
3. 按 `oh-my-claw-mvp-implementation-plan.md` 开始 Phase 1 的 M0 / M1
4. 使用 `oh-my-claw-acceptance-test-plan.md` 作为 Phase 1 验收标准

---

## 7. 文档维护约定（建议）

后续如果继续推进，建议遵守以下规则：

- 涉及系统边界变化时，先改 `oh-my-claw-architecture.md`
- 涉及 workflow 行为变化时，先改 `oh-my-claw-workflow-specs.md`
- 涉及验收口径变化时，先改 `oh-my-claw-acceptance-test-plan.md`
- 涉及配置行为变化时，先改 `oh-my-claw-config-spec.md`
- 涉及推进顺序变化时，先改 `oh-my-claw-mvp-phases.md` 或 `milestones-and-issues.md`

这样可以避免“实现已经变了，但文档体系失真”的问题。

---

## 8. 总结

当前 `oh-my-claw` 仓库已经不是一个只有想法的空仓库，而是一个：

> **拥有完整 MVP 设计、实施、验收、配置和 backlog 文档的可执行项目规格库。**

现在最合理的推进方式，不再是继续发散式讨论，而是：

- 开始 issue 化
- 开始 milestone 化
- 进入 Phase 1 执行
