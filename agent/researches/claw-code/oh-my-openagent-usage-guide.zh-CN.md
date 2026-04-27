# oh-my-openagent 使用指导

基于仓库 `/home/zq/work-space/repo/ai-projs/posp/claw-code/oh-my-openagent` 的 README、安装指南、编排指南、模型匹配指南、配置参考和 CLI 参考整理。

## 1. 它到底是什么

`oh-my-openagent` 不是一个“换壳 prompt 包”，而是 OpenCode 上的一套多智能体编排系统。

它的核心思路是：

- 用 `Sisyphus` 做总调度
- 用 `Prometheus` 先规划
- 用 `Atlas` 按计划执行
- 用 `Hephaestus` 处理深度实现
- 用 `Oracle` 做架构/复杂问题咨询
- 用 `Explore` / `Librarian` 做快速搜索和资料检索
- 用 `visual-engineering` 类别专门处理前端/视觉任务

真正强的地方，不是“模型更贵”，而是“不同模型做不同角色”。

## 2. 先记住三种用法

### 2.1 日常复杂任务：`ulw`

这是默认推荐路径，适合大多数复杂任务。

示例：

```text
ulw fix flaky tests in auth module, preserve behavior, run tests
ulw implement JWT authentication following existing patterns
ulw add a deploy subcommand and update docs
```

适合场景：

- 任务复杂，但边界大致清楚
- 你懒得手写完整方案
- 你希望它自己探索代码库、分配子任务、执行并验证

### 2.2 高精度任务：`@plan` -> `/start-work`

这是最强、最稳的工作流，适合重要改动。

示例：

```text
@plan "refactor billing service, keep API stable, define rollback and verification"
```

然后执行：

```text
/start-work
```

适合场景：

- 大型重构
- 生产级高风险改动
- 多天任务
- 需要清晰计划、检查点、决策痕迹

这条链路的分工是：

- `Prometheus` 采访式澄清需求并生成计划
- `Metis` 查漏补缺
- `Momus` 做苛刻审查
- `Atlas` 按计划推进执行

### 2.3 深度疑难问题：切到 `Hephaestus`

当问题更像“深度技术推理”，而不是“普通任务编排”时，优先切到 `Hephaestus`。

适合场景：

- 跨很多文件的复杂 bug
- 架构级推理
- 深度性能/并发/一致性问题
- 你明确想利用 GPT-5.4 一类模型的推理风格

不要把所有任务都交给 `Hephaestus`。大多数任务还是 `ulw` 更合适。

## 3. 发挥最强能力的正确顺序

### 3.1 安装

```bash
bunx oh-my-opencode install
```

注意：

- 发布包和 CLI 名仍然是 `oh-my-opencode`
- 但 `opencode.json` 里的插件入口应优先使用 `oh-my-openagent`

### 3.2 立即体检

```bash
bunx oh-my-opencode doctor --verbose
```

这一步很重要。它会帮你检查：

- OpenCode 版本是否满足要求
- 插件是否注册成功
- 配置文件是否有效
- 模型解析和回退链是否合理
- 工具、MCP、LSP 是否可用

### 3.3 新项目先跑 `/init-deep`

```text
/init-deep
```

它会按目录层级生成 `AGENTS.md`，让智能体自动获得局部上下文。

这一步的价值很高：

- 降低你手动解释项目结构的成本
- 提高多目录、多模块任务的稳定性
- 减少上下文窗口浪费

### 3.4 再开始干活

推荐顺序：

1. `doctor`
2. `/init-deep`
3. 简单复杂任务直接 `ulw`
4. 大任务使用 `@plan` -> `/start-work`
5. 会话中断前用 `/handoff`

## 4. 最重要的模型分工原则

### 4.1 编排型角色

这些更适合 Claude / Kimi / GLM 一类“擅长遵守长指令和流程”的模型：

- `Sisyphus`
- `Prometheus`
- `Atlas`
- `Metis`

### 4.2 深推理角色

这些更适合 GPT-5.4 一类“深度自主推理”的模型：

- `Hephaestus`
- `Oracle`
- `Momus`
- `deep`
- `ultrabrain`

### 4.3 速度型角色

这些要快、便宜，不需要最贵模型：

- `Explore`
- `Librarian`
- `quick`
- `writing`

### 4.4 视觉型角色

前端、UI、视觉设计任务优先交给：

- `visual-engineering`
- `Multimodal-Looker`

通常 Gemini 系列更合适。

## 5. 真正拉开差距的配置

下面这几个开关的收益最高。

### 5.1 开启 Hashline 编辑

```jsonc
{
  "hashline_edit": true
}
```

这是它最有价值的能力之一。核心作用是通过 `LINE#ID` 哈希锚点防止“改错行”“文件变了还照旧写”的问题。

### 5.2 开启运行时回退

```jsonc
{
  "runtime_fallback": true
}
```

多模型系统如果没有回退链，真实稳定性会大打折扣。

### 5.3 开启任务系统和激进截断

```jsonc
{
  "experimental": {
    "aggressive_truncation": true,
    "task_system": true
  }
}
```

作用：

- 控制上下文膨胀
- 让长任务更容易继续推进
- 给多阶段执行更好的状态保持

### 5.4 配置合理并发

```jsonc
{
  "background_task": {
    "defaultConcurrency": 8,
    "providerConcurrency": {
      "anthropic": 3,
      "openai": 3,
      "google": 5,
      "opencode": 10
    }
  }
}
```

不要一味拉满。并发太高会带来：

- 成本上升
- 速率限制
- 结果回收变乱

推荐原则：

- 贵模型低并发
- 便宜/快速模型高并发
- 高风险项目保守一点

### 5.5 在 tmux 中使用

如果你经常跑后台子代理，建议打开：

```jsonc
{
  "tmux": {
    "enabled": true,
    "layout": "main-vertical"
  }
}
```

前提是你本来就在 `tmux` 环境里，并通过 `opencode --port <port>` 运行。这样你可以直接观察多个后台智能体并行工作。

## 6. 推荐配置模板

适合作为大多数编码项目的起点：

```jsonc
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/assets/oh-my-opencode.schema.json",

  "agents": {
    "sisyphus": {
      "model": "anthropic/claude-opus-4-7",
      "ultrawork": { "model": "anthropic/claude-opus-4-7", "variant": "max" }
    },
    "hephaestus": {
      "model": "openai/gpt-5.4",
      "prompt_append": "Explore thoroughly, then implement. Prefer small, testable changes."
    },
    "oracle": { "model": "openai/gpt-5.4", "variant": "high" },
    "librarian": { "model": "google/gemini-3-flash" },
    "explore": { "model": "github-copilot/grok-code-fast-1" },
    "multimodal-looker": { "model": "google/gemini-3.1-pro" }
  },

  "categories": {
    "quick": { "model": "opencode/gpt-5-nano" },
    "unspecified-low": { "model": "anthropic/claude-sonnet-4-6" },
    "unspecified-high": { "model": "anthropic/claude-opus-4-7", "variant": "max" },
    "writing": { "model": "google/gemini-3-flash" },
    "visual-engineering": { "model": "google/gemini-3.1-pro", "variant": "high" },
    "deep": { "model": "openai/gpt-5.4" },
    "ultrabrain": { "model": "openai/gpt-5.4", "variant": "xhigh" }
  },

  "background_task": {
    "providerConcurrency": {
      "anthropic": 3,
      "openai": 3,
      "google": 5,
      "opencode": 10
    }
  },

  "hashline_edit": true,
  "runtime_fallback": true,
  "experimental": {
    "aggressive_truncation": true,
    "task_system": true
  }
}
```

## 7. 任务描述怎么写，效果最好

好的写法：

```text
ulw fix failing tests in auth module, preserve external behavior, run tests and summarize root cause
```

```text
ulw add JWT authentication following repository patterns, keep middleware structure consistent, update tests and docs
```

```text
@plan "split the monolithic billing service into modules, preserve public API, define migration steps, rollback plan, and verification strategy"
```

高质量任务描述建议包含：

- 目标
- 边界
- 不允许破坏什么
- 需要验证什么
- 是否遵循现有模式

## 8. 常用命令

```bash
bunx oh-my-opencode install
bunx oh-my-opencode doctor
bunx oh-my-opencode doctor --verbose
bunx oh-my-opencode refresh-model-capabilities
bunx oh-my-opencode run "ulw fix flaky tests in auth module"
```

会话内常用：

```text
ulw
@plan "..."
/start-work
/init-deep
/handoff
/ulw-loop
/refactor
```

## 9. 明确的反模式

不要这样用：

- 把它当成单模型聊天助手
- 不做 `doctor` 就开始排查奇怪问题
- 给 `Explore` / `Librarian` 配最贵模型
- 把 `Hephaestus` 强行换成 Claude
- 关掉 `no-sisyphus-gpt` 这类保护钩子
- 同目录同时保留新旧两个插件配置文件名
- 大任务不做 `/init-deep` 和计划，直接裸冲

## 10. 我的建议

如果你只想记住最少的东西，就记住这套：

1. 装完先 `doctor`
2. 新项目先 `/init-deep`
3. 大多数复杂任务直接 `ulw`
4. 关键任务使用 `@plan` -> `/start-work`
5. 开 `hashline_edit`
6. 开 `runtime_fallback`
7. 保持模型角色匹配，不要乱配

## 11. 仓库内最值得看的文档

- `README.zh-cn.md`
- `docs/guide/installation.md`
- `docs/guide/overview.md`
- `docs/guide/orchestration.md`
- `docs/guide/agent-model-matching.md`
- `docs/reference/configuration.md`
- `docs/reference/cli.md`
- `docs/reference/features.md`
