# 大模型定价、限制与 20 人团队月度 Token 用量评估

生成时间：2026-04-15
输出路径：`./llm_pricing_usage_report.md`

## 0. 结论摘要

1. 你给出的三个型号中，只有 `GLM-5.1` 可以确认是公开可见型号；`Claude-opus-4.6` 与 `GPT-5.4` 都不是对应厂商当前公开的官方命名。
2. 为了保证横向对比可落地，本报告采用如下“官方/近似等价”口径：
   - `GLM-5.1`：保留原型号，但价格与上下文参数采用可公开抓取的 OpenRouter 转售页面口径；直连 Z.ai / BigModel 官方计费应以控制台实时信息为准。
   - `Claude-opus-4.6`：按最接近的官方现行型号 `Claude Opus 4.1` 对比。
   - `GPT-5.4`：按最接近的官方现行型号 `GPT-5` 对比。
3. 对一个 20 人研发团队，按“需求生成 + 开发/Review loop + 测试验证”三环节估算：
   - 保守：约 `64.24M tokens/月`
   - 基线：约 `94.60M tokens/月`
   - 激进：约 `171.60M tokens/月`
4. 按基线场景、不考虑缓存命中与 Batch 折扣，仅按公开 input/output 单价估算月成本：
   - GLM-5.1（OpenRouter 转售口径）：约 `$143.11/月`
   - Claude Opus 4.1（官方口径）：约 `$2,871.00/月`
   - GPT-5（官方口径）：约 `$330.00/月`
5. 若团队实际工作流中存在“长 system prompt + 大仓库上下文 + 同一 PR 多轮 review”，缓存/上下文复用会显著影响最终成本，尤其是 Claude 与 GPT 系列。

---

## 1. 研究口径与边界

### 1.1 本报告优先级
- 第一优先：厂商官方公开文档 / 官方定价页
- 第二优先：公开可抓取、信誉较高的聚合平台页面（仅在官方页面无法稳定抓取时使用）

### 1.2 需要特别说明的命名问题

#### Claude-opus-4.6
未发现 Anthropic 官方公开型号名为 `Claude Opus 4.6`。Anthropic 当前公开的 Opus 线官方型号为 `Claude Opus 4` / `Claude Opus 4.1`。因此本报告采用 `Claude Opus 4.1` 作为近似等价比较对象。

#### GPT-5.4
未发现 OpenAI 官方公开型号名为 `GPT-5.4`。OpenAI 当前公开命名口径为 `GPT-5 / GPT-5 mini / GPT-5 nano / GPT-5 pro` 等。因此本报告采用 `GPT-5` 作为近似等价比较对象。

#### GLM-5.1
`GLM-5.1` 可在智谱 / Z.ai 开发文档导航中确认存在，但官方公开定价页未能在当前环境中稳定提取出结构化计费明细。因此：
- “模型存在性”采用 BigModel / Z.ai 官方文档口径；
- “价格、上下文、最大输出”采用 OpenRouter 上的 `z-ai/glm-5.1` 页面口径；
- 直连 Z.ai / BigModel 实际结算价格、限流、配额仍需以官方控制台为准。

---

## 2. 定价与限制对比

### 2.1 汇总表

| 用户给定型号 | 官方状态 | 本报告采用对比型号 | 输入价格 | 输出价格 | 缓存价格 | 上下文窗口 | 最大输出 | 限流/限制口径 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| GLM-5.1 | 型号存在，但公开官方价格抓取不稳定 | GLM-5.1 | $0.95 / 1M input | $3.15 / 1M output | Cache read: $0.475 / 1M | 202,752 tokens | 65,535 tokens | 公开统一 RPM/TPM 未明确抓到；大概率按账户/项目配额执行 |
| Claude-opus-4.6 | 非 Anthropic 官方公开命名 | Claude Opus 4.1 | $15 / 1M input | $75 / 1M output | 5 分钟 cache write: $18.75 / 1M；1 小时 cache write: $30 / 1M；cache read: $1.50 / 1M | 200K tokens | 32K tokens | Anthropic 按 tier 分配 RPM / ITPM / OTPM，非统一固定值 |
| GPT-5.4 | 非 OpenAI 官方公开命名 | GPT-5 | $1.25 / 1M input | $10 / 1M output | Cached input: $0.125 / 1M | 400K tokens | 128K tokens | OpenAI 按账户 / tier / org limits 动态分配，非统一固定值 |

### 2.2 逐模型说明

#### A. GLM-5.1

已确认信息：
- BigModel / Z.ai 开发文档导航中存在 `GLM-5.1` 文本模型条目。
- OpenRouter 的 `z-ai/glm-5.1` 页面可公开抓取到以下信息：
  - Input: `$0.95 / 1M tokens`
  - Output: `$3.15 / 1M tokens`
  - Cache read: `$0.475 / 1M tokens`
  - Context: `202,752 tokens`
  - Max output: `65,535 tokens`

限制与注意事项：
- 以上价格与上下文参数来自聚合转售平台，不等价于 Z.ai / BigModel 直连价格。
- 当前未抓取到公开统一的官方 RPM / TPM / 并发上限；实际多半取决于账号等级、项目配额或控制台策略。
- 如果你最终走的是国内直连计费，而不是 OpenRouter 路由，则账单与速率限制可能有明显偏差。

建议报告口径：
- 将 GLM-5.1 标记为“型号官方存在，但本报告价格采用 OpenRouter 转售口径，仅作横向参考”。

#### B. Claude Opus 4.1（替代 Claude-opus-4.6）

已确认信息：
- Anthropic 官方未见 `Claude Opus 4.6` 公开型号。
- Anthropic 官方 pricing 页面可抓到 `Opus 4.1`：
  - Input: `$15 / MTok`
  - Output: `$75 / MTok`
  - Prompt caching write: `$18.75 / MTok`
  - Prompt caching read: `$1.50 / MTok`
- Anthropic 官方模型文档口径：
  - Context window: `200K`
  - Max output: `32K`
- Anthropic rate limits 官方说明口径：
  - 按 organization tier 区分
  - 以 `RPM / ITPM / OTPM` 管理
  - 还存在 acceleration limits

限制与注意事项：
- 如果走 AWS Bedrock / Vertex AI，价格与限额会和 Anthropic 直连 API 不同。
- Prompt caching 的 write/read 计费与基础 input/output 计费分开看，不能直接混为单一 input 单价。
- 新账号可用额度通常低于成熟账号。

#### C. GPT-5（替代 GPT-5.4）

已确认信息：
- OpenAI 官方未见 `GPT-5.4` 公开型号。
- 以 `GPT-5` 作为近似等价比较对象，公开定价口径为：
  - Input: `$1.25 / 1M tokens`
  - Cached input: `$0.125 / 1M tokens`
  - Output: `$10 / 1M tokens`
- 官方模型文档口径：
  - Context window: `400,000 tokens`
  - Max output: `128,000 tokens`
- Rate limits：
  - 无统一对外固定数值
  - 以账号、tier、组织级 limits 为准

限制与注意事项：
- 若第三方平台显示 `gpt-5.4`，通常是平台自定义 alias 或路由标签，不是 OpenAI 官方 SKU。
- 不同服务层（普通 API、Scale Tier、Batch、第三方路由）价格与吞吐配额可能不同。

---

## 3. 20 人团队月度 Token 用量评估方法

### 3.1 团队规模与时间假设
- 团队人数：`20 人`
- 工作日：`22 天 / 月`
- 口径：按“每人每天与模型的有效交互次数 × 单次平均输入/输出 tokens”估算

### 3.2 三个业务环节拆分

#### 需求生成
覆盖两类典型任务：
- 跨架构对比分析
- 性能缺陷定位

#### 代码开发
覆盖两类典型任务：
- 开发实现
- Code Review / 反复修改 loop

#### 测试验证
覆盖两类典型任务：
- 环境配置 / 排障
- 测例编写 / 调整

### 3.3 三档场景设定

#### 保守场景
适用于：
- 团队刚开始接入大模型
- 主要把模型当问答与局部代码补全工具
- Review 与测试阶段还未形成高度自动化 loop

#### 基线场景
适用于：
- 模型已进入日常研发流程
- 需求分析、开发、Review、测试都有稳定使用
- 存在中等强度多轮对话与上下文回放

#### 激进场景
适用于：
- 模型深度嵌入研发主流程
- 需求/设计/开发/Review/测试基本全程高频调用
- 大量长上下文、多轮修复、多轮 Review、多轮测试重跑

---

## 4. 用量假设明细

### 4.1 保守场景：单人单日

| 环节 | 子任务 | 次数/天 | 单次输入 | 单次输出 |
|---|---|---:|---:|---:|
| 需求生成 | 跨架构对比分析 | 1 | 12,000 | 4,000 |
| 需求生成 | 性能缺陷定位 | 1 | 8,000 | 3,000 |
| 代码开发 | 开发 | 5 | 7,000 | 2,500 |
| 代码开发 | Review loop | 3 | 9,000 | 2,500 |
| 测试验证 | 环境配置 | 2 | 6,000 | 2,000 |
| 测试验证 | 测例编写 | 3 | 5,000 | 2,000 |

### 4.2 基线场景：单人单日

| 环节 | 子任务 | 次数/天 | 单次输入 | 单次输出 |
|---|---|---:|---:|---:|
| 需求生成 | 跨架构对比分析 | 1 | 15,000 | 6,000 |
| 需求生成 | 性能缺陷定位 | 1 | 12,000 | 5,000 |
| 代码开发 | 开发 | 6 | 8,000 | 3,000 |
| 代码开发 | Review loop | 4 | 10,000 | 3,000 |
| 测试验证 | 环境配置 | 3 | 7,000 | 2,000 |
| 测试验证 | 测例编写 | 4 | 6,000 | 2,000 |

### 4.3 激进场景：单人单日

| 环节 | 子任务 | 次数/天 | 单次输入 | 单次输出 |
|---|---|---:|---:|---:|
| 需求生成 | 跨架构对比分析 | 2 | 18,000 | 7,000 |
| 需求生成 | 性能缺陷定位 | 2 | 14,000 | 6,000 |
| 代码开发 | 开发 | 8 | 10,000 | 3,500 |
| 代码开发 | Review loop | 6 | 12,000 | 3,500 |
| 测试验证 | 环境配置 | 4 | 8,000 | 2,500 |
| 测试验证 | 测例编写 | 6 | 7,000 | 2,500 |

---

## 5. 月度 Token 消耗评估结果

### 5.1 保守场景（月度）

| 环节 | 月输入 tokens | 月输出 tokens | 月总 tokens |
|---|---:|---:|---:|
| 需求生成 | 8.80M | 3.08M | 11.88M |
| 代码开发 | 27.28M | 8.80M | 36.08M |
| 测试验证 | 11.88M | 4.40M | 16.28M |
| 合计 | 47.96M | 16.28M | 64.24M |

### 5.2 基线场景（月度）

| 环节 | 月输入 tokens | 月输出 tokens | 月总 tokens |
|---|---:|---:|---:|
| 需求生成 | 11.88M | 4.84M | 16.72M |
| 代码开发 | 38.72M | 13.20M | 51.92M |
| 测试验证 | 19.80M | 6.16M | 25.96M |
| 合计 | 70.40M | 24.20M | 94.60M |

### 5.3 激进场景（月度）

| 环节 | 月输入 tokens | 月输出 tokens | 月总 tokens |
|---|---:|---:|---:|
| 需求生成 | 28.16M | 11.44M | 39.60M |
| 代码开发 | 66.88M | 21.56M | 88.44M |
| 测试验证 | 32.56M | 11.00M | 43.56M |
| 合计 | 127.60M | 44.00M | 171.60M |

### 5.4 结构观察

无论保守、基线还是激进场景，消耗占比最高的通常都是 `代码开发 + Review loop`，原因有三：
1. 交互轮次最多；
2. 需要反复携带代码片段、报错日志、PR diff、修改后的新上下文；
3. Review 阶段天然容易形成多轮闭环，导致输入 token 被不断重复放大。

---

## 6. 基于公开单价的月成本映射

说明：
- 仅按 input/output 单价估算
- 不含税
- 不考虑缓存命中、缓存写入、Batch 折扣、企业包量、第三方平台加价、重试失败损耗
- GLM-5.1 采用 OpenRouter 转售口径，仅作参考

### 6.1 三档场景总成本

| 场景 | GLM-5.1（OpenRouter） | Claude Opus 4.1 | GPT-5 |
|---|---:|---:|---:|
| 保守 | $96.84 | $1,940.40 | $222.75 |
| 基线 | $143.11 | $2,871.00 | $330.00 |
| 激进 | $259.82 | $5,214.00 | $599.50 |

### 6.2 基线场景分环节成本

| 环节 | GLM-5.1（OpenRouter） | Claude Opus 4.1 | GPT-5 |
|---|---:|---:|---:|
| 需求生成 | $26.53 | $541.20 | $63.25 |
| 代码开发 | $78.36 | $1,570.80 | $180.40 |
| 测试验证 | $38.21 | $759.00 | $86.35 |
| 合计 | $143.11 | $2,871.00 | $330.00 |

---

## 7. 采购与落地建议

### 7.1 如果目标是“成本最优”
可优先考虑：
- 高频开发、批量代码理解、常规测试辅助：`GLM-5.1` 或 `GPT-5`
- 其中 `GLM-5.1` 在本报告采用的转售口径下价格最低，但请务必复核直连官方账单与配额。

### 7.2 如果目标是“高质量复杂推理/复杂 review”
可考虑：
- 将 `Claude Opus 4.1` 作为高难问题、关键设计评审、复杂 review 的升级路径
- 不建议把 Opus 作为 20 人团队所有日常 coding/review 的默认底座，否则成本会明显高于 GPT-5 / GLM-5.1

### 7.3 推荐的分层用法
更现实的团队配置通常不是“单模型全覆盖”，而是：
- 日常开发、测试、常规 review：低成本主力模型
- 难题定位、架构评审、核心 PR 复审：高质量模型

一个典型组合是：
- `GPT-5` 或 `GLM-5.1` 做默认模型
- `Claude Opus 4.1` 仅用于：
  - 复杂架构方案对比
  - 线上性能疑难定位
  - 核心模块高风险 PR 的二次 review

### 7.4 成本控制建议
1. 尽量开启缓存 / prompt 复用
2. 把大仓库上下文切分成“必要最小片段”
3. 对 review loop 设置最大轮次
4. 将“环境配置排障”与“测例编写”拆分到更便宜模型上
5. 仅在需要长链推理和高复杂度审查时升级到 Opus

---

## 8. 风险与不确定性

1. `Claude-opus-4.6` 与 `GPT-5.4` 不是官方公开命名，若你内部采购的是第三方路由平台别名，则实际账单和限额必须以采购平台合同/控制台为准。
2. `GLM-5.1` 的价格在本报告中采用了可公开抓取的 OpenRouter 页面，不代表 Z.ai / BigModel 直连官方结算价。
3. OpenAI、Anthropic 的 rate limits 普遍是 `tier-based / account-specific`，不能简单写成单一固定 RPM/TPM。
4. 本报告的 token 用量模型是“团队过程估算”，不是日志回放结果；若你提供过去一个月的实际调用日志，我可以进一步校准成更贴近你团队的预算模型。

---

## 9. 参考来源

### 官方 / 主要来源
- Z.ai / BigModel 开发文档入口：
  - https://open.bigmodel.cn/dev/api
- Anthropic 官方定价页：
  - https://www.anthropic.com/pricing
- Anthropic 官方模型总览：
  - https://docs.anthropic.com/en/docs/about-claude/models/all-models
- Anthropic 官方 rate limits：
  - https://docs.anthropic.com/en/api/rate-limits
- Anthropic Prompt Caching 文档：
  - https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- OpenAI 官方定价页：
  - https://openai.com/api/pricing/
- OpenAI 官方模型文档：
  - https://platform.openai.com/docs/models
- OpenAI 官方 rate limits 指引：
  - https://platform.openai.com/docs/guides/rate-limits
- OpenAI 组织 limits 页面（账号相关）：
  - https://platform.openai.com/settings/organization/limits

### 辅助 / 次级来源
- OpenRouter `z-ai/glm-5.1`：
  - https://openrouter.ai/z-ai/glm-5.1

---

## 10. 可继续深化的下一步

如果你愿意，我下一步可以继续在当前目录补一份：
1. `llm_pricing_usage_report_ppt_outline.md`：适合向管理层汇报的 8~10 页 PPT 大纲
2. `llm_pricing_usage_report_budget_model.md`：把人均调用次数、缓存命中率、review loop 次数做成可调参数预算模型
3. `llm_model_selection_recommendation.md`：针对“需求、开发、测试”三个环节给出具体选型建议和混合部署策略
