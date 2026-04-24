# RV-Insights 测试方案

## 1. 测试策略金字塔

```mermaid
flowchart TD
    subgraph 金字塔 [测试金字塔]
        direction TB
        E2E["E2E测试 (5%)\nPlaywright\n关键用户旅程"]
        Integration["集成测试 (25%)\nVitest + Supertest\nAPI/DB/队列/Agent"]
        Unit["单元测试 (70%)\nVitest\n服务/工具/组件"]
    end

    style Unit fill:#4ade80
    style Integration fill:#fbbf24
    style E2E fill:#f87171
```

| 测试层级 | 占比 | 目标覆盖率 | 执行时间 | 执行时机 |
|----------|------|------------|----------|----------|
| **单元测试** | 70% | ≥85% | <2分钟 | 每次提交前本地运行 |
| **集成测试** | 25% | ≥80% | 3-5分钟 | CI中自动运行 |
| **E2E测试** | 5% | 核心流程100% | 5-8分钟 | CI中自动运行 |
| **Agent行为测试** | 附加 | 关键决策路径 | 10-15分钟 | 夜间/发布前 |

## 2. 单元测试

### 2.1 测试框架配置

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      thresholds: {
        lines: 85,
        functions: 85,
        branches: 80,
        statements: 85
      },
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mocks/**',
        '**/types/**'
      ]
    },
    setupFiles: ['./test/setup.ts']
  }
})
```

### 2.2 核心服务测试

#### Orchestration Service

```typescript
// test/services/orchestration-service.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { OrchestrationService } from '@/services/orchestration'
import { createMockContribution, createMockStageExecution } from '@/test/factories'

describe('OrchestrationService', () => {
  let service: OrchestrationService
  let mockDb: any
  let mockRedis: any

  beforeEach(() => {
    mockDb = {
      contributions: { findById: vi.fn(), update: vi.fn() },
      stageExecutions: { create: vi.fn(), update: vi.fn() }
    }
    mockRedis = { publish: vi.fn() }
    service = new OrchestrationService(mockDb, mockRedis)
  })

  describe('startStage', () => {
    it('should create stage execution and publish event', async () => {
      const contribution = createMockContribution({ status: 'draft' })
      mockDb.contributions.findById.mockResolvedValue(contribution)
      mockDb.stageExecutions.create.mockResolvedValue({ id: 'stage-1' })

      const result = await service.startStage(contribution.id, 'exploration')

      expect(result.stageType).toBe('exploration')
      expect(result.status).toBe('running')
      expect(mockDb.stageExecutions.create).toHaveBeenCalledWith(
        expect.objectContaining({
          contributionId: contribution.id,
          stageType: 'exploration',
          status: 'running'
        })
      )
      expect(mockRedis.publish).toHaveBeenCalledWith(
        'stage.started',
        expect.any(String)
      )
    })

    it('should throw if contribution not found', async () => {
      mockDb.contributions.findById.mockResolvedValue(null)

      await expect(
        service.startStage('non-existent', 'exploration')
      ).rejects.toThrow('Contribution not found')
    })

    it('should throw if stage transition is invalid', async () => {
      const contribution = createMockContribution({ status: 'completed' })
      mockDb.contributions.findById.mockResolvedValue(contribution)

      await expect(
        service.startStage(contribution.id, 'exploration')
      ).rejects.toThrow('Invalid stage transition')
    })
  })

  describe('completeStage', () => {
    it('should update status to awaiting_review and trigger guardrail', async () => {
      const stage = createMockStageExecution({ status: 'running' })
      mockDb.stageExecutions.findById.mockResolvedValue(stage)

      await service.completeStage(stage.id, { candidates: [] })

      expect(mockDb.stageExecutions.update).toHaveBeenCalledWith(
        stage.id,
        expect.objectContaining({
          status: 'awaiting_review',
          output: { candidates: [] }
        })
      )
    })
  })
})
```

#### Review Gate Service

```typescript
// test/services/review-gate-service.test.ts
describe('ReviewGateService', () => {
  describe('submitReview', () => {
    it('should approve stage and trigger next stage', async () => {
      const service = new ReviewGateService(mockDb, mockOrchestrator)
      const stage = createMockStageExecution({ status: 'awaiting_review' })

      mockDb.stageExecutions.findById.mockResolvedValue(stage)

      const result = await service.submitReview({
        stageExecutionId: stage.id,
        decision: 'approve',
        comment: 'LGTM'
      })

      expect(result.decision).toBe('approve')
      expect(mockOrchestrator.advanceToNextStage).toHaveBeenCalledWith(stage.contributionId)
    })

    it('should reject stage and mark contribution failed', async () => {
      const service = new ReviewGateService(mockDb, mockOrchestrator)
      const stage = createMockStageExecution({ status: 'awaiting_review' })

      mockDb.stageExecutions.findById.mockResolvedValue(stage)

      await service.submitReview({
        stageExecutionId: stage.id,
        decision: 'reject',
        comment: '方向错误'
      })

      expect(mockOrchestrator.markFailed).toHaveBeenCalledWith(
        stage.contributionId,
        'Rejected by human review'
      )
    })

    it('should request changes and restart stage', async () => {
      const service = new ReviewGateService(mockDb, mockOrchestrator)
      const stage = createMockStageExecution({ status: 'awaiting_review' })

      mockDb.stageExecutions.findById.mockResolvedValue(stage)

      await service.submitReview({
        stageExecutionId: stage.id,
        decision: 'request_changes',
        comment: '请补充边界条件处理'
      })

      expect(mockOrchestrator.restartStage).toHaveBeenCalledWith(
        stage.contributionId,
        stage.stageType,
        { feedback: '请补充边界条件处理' }
      )
    })
  })
})
```

### 2.3 状态机测试

```typescript
// test/domain/contribution-state-machine.test.ts
import { ContributionStateMachine } from '@/domain/state-machine'
import { describe, it, expect } from 'vitest'

describe('ContributionStateMachine', () => {
  const validTransitions = [
    { from: 'draft', to: 'exploring', event: 'start' },
    { from: 'exploring', to: 'exploration_review', event: 'stage_complete' },
    { from: 'exploration_review', to: 'planning', event: 'approve' },
    { from: 'exploration_review', to: 'rejected', event: 'reject' },
    { from: 'planning', to: 'planning_review', event: 'stage_complete' },
    { from: 'planning_review', to: 'developing', event: 'approve' },
    { from: 'developing', to: 'development_review', event: 'iteration_complete' },
    { from: 'development_review', to: 'developing', event: 'request_changes' },
    { from: 'development_review', to: 'testing', event: 'approve' },
    { from: 'testing', to: 'testing_review', event: 'stage_complete' },
    { from: 'testing_review', to: 'completed', event: 'approve' },
    { from: 'testing_review', to: 'testing', event: 'request_changes' },
  ]

  it.each(validTransitions)(
    'should allow transition from $from to $to on $event',
    ({ from, to, event }) => {
      const sm = new ContributionStateMachine(from)
      expect(sm.can(event)).toBe(true)
      sm.transition(event)
      expect(sm.state).toBe(to)
    }
  )

  const invalidTransitions = [
    { from: 'draft', to: 'planning', event: 'approve' },
    { from: 'exploring', to: 'completed', event: 'approve' },
    { from: 'completed', to: 'exploring', event: 'start' },
  ]

  it.each(invalidTransitions)(
    'should NOT allow transition from $from to $to on $event',
    ({ from, event }) => {
      const sm = new ContributionStateMachine(from)
      expect(sm.can(event)).toBe(false)
      expect(() => sm.transition(event)).toThrow()
    }
  )
})
```

### 2.4 工具函数测试

```typescript
// test/utils/diff-parser.test.ts
describe('DiffParser', () => {
  it('should parse unified diff correctly', () => {
    const diff = `diff --git a/arch/riscv/kernel/smp.c b/arch/riscv/kernel/smp.c
index abc..def 100644
--- a/arch/riscv/kernel/smp.c
+++ b/arch/riscv/kernel/smp.c
@@ -100,7 +100,8 @@ void smp_boot(void)
 	int cpu = smp_processor_id();
-	spin_lock(&boot_lock);
+	if (!spin_trylock(&boot_lock))
+		return -EBUSY;
 	...`

    const result = parseDiff(diff)

    expect(result.files).toHaveLength(1)
    expect(result.files[0].oldPath).toBe('a/arch/riscv/kernel/smp.c')
    expect(result.files[0].newPath).toBe('b/arch/riscv/kernel/smp.c')
    expect(result.files[0].hunks).toHaveLength(1)
    expect(result.files[0].hunks[0].oldStart).toBe(100)
    expect(result.files[0].hunks[0].oldLines).toBe(7)
  })

  it('should handle empty diff', () => {
    expect(() => parseDiff('')).toThrow('Invalid diff format')
  })
})
```

## 3. 集成测试

### 3.1 API端点测试

```typescript
// test/integration/api/contributions.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { buildApp } from '@/app'
import { setupTestDb, teardownTestDb } from '@/test/database'
import { createAuthToken } from '@/test/auth'

describe('Contributions API', () => {
  let app: any
  let db: any
  let authToken: string

  beforeAll(async () => {
    db = await setupTestDb()
    app = await buildApp({ database: db })
    authToken = createAuthToken({ userId: 'test-user', role: 'user' })
  })

  afterAll(async () => {
    await teardownTestDb(db)
  })

  describe('POST /api/v1/contributions', () => {
    it('should create contribution with valid input', async () => {
      const response = await app.inject({
        method: 'POST',
        url: '/api/v1/contributions',
        headers: { authorization: `Bearer ${authToken}` },
        payload: {
          projectId: 'test-project-id',
          title: '测试贡献任务',
          description: '这是一个测试',
          config: { maxIterations: 3 }
        }
      })

      expect(response.statusCode).toBe(201)
      const body = JSON.parse(response.body)
      expect(body.id).toBeDefined()
      expect(body.status).toBe('draft')
      expect(body.title).toBe('测试贡献任务')
    })

    it('should reject invalid input', async () => {
      const response = await app.inject({
        method: 'POST',
        url: '/api/v1/contributions',
        headers: { authorization: `Bearer ${authToken}` },
        payload: {
          title: '', // 空标题
          projectId: 'invalid-uuid'
        }
      })

      expect(response.statusCode).toBe(400)
      const body = JSON.parse(response.body)
      expect(body.error).toContain('title')
    })

    it('should reject unauthorized requests', async () => {
      const response = await app.inject({
        method: 'POST',
        url: '/api/v1/contributions',
        payload: { title: '测试' }
      })

      expect(response.statusCode).toBe(401)
    })
  })

  describe('POST /api/v1/contributions/:id/review', () => {
    it('should approve stage and advance workflow', async () => {
      // 创建测试数据
      const contribution = await db.contributions.create({
        userId: 'test-user',
        status: 'exploration_review',
        title: '测试'
      })
      const stage = await db.stageExecutions.create({
        contributionId: contribution.id,
        stageType: 'exploration',
        status: 'awaiting_review'
      })

      const response = await app.inject({
        method: 'POST',
        url: `/api/v1/contributions/${contribution.id}/review`,
        headers: { authorization: `Bearer ${authToken}` },
        payload: {
          stageExecutionId: stage.id,
          decision: 'approve',
          comment: '测试通过'
        }
      })

      expect(response.statusCode).toBe(200)

      // 验证状态流转
      const updated = await db.contributions.findById(contribution.id)
      expect(updated.status).toBe('planning')
    })
  })
})
```

### 3.2 数据库测试（Testcontainers）

```typescript
// test/integration/database/stage-execution.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { PostgreSqlContainer } from '@testcontainers/postgresql'
import { drizzle } from 'drizzle-orm/node-postgres'
import { migrate } from 'drizzle-orm/node-postgres/migrator'

describe('StageExecution Repository', () => {
  let container: any
  let db: any

  beforeAll(async () => {
    container = await new PostgreSqlContainer()
      .withDatabase('rv_insights_test')
      .start()

    const connectionString = container.getConnectionUri()
    db = drizzle(connectionString)
    await migrate(db, { migrationsFolder: './drizzle' })
  }, 30000)

  afterAll(async () => {
    await container.stop()
  })

  it('should create and retrieve stage execution', async () => {
    const stage = await db.insert(stageExecutions).values({
      contributionId: 'test-contribution',
      stageType: 'exploration',
      status: 'running',
      iteration: 0,
      input: { query: 'test' }
    }).returning()

    expect(stage[0].id).toBeDefined()
    expect(stage[0].status).toBe('running')

    const retrieved = await db.select().from(stageExecutions)
      .where(eq(stageExecutions.id, stage[0].id))

    expect(retrieved).toHaveLength(1)
    expect(retrieved[0].stageType).toBe('exploration')
  })
})
```

### 3.3 消息队列测试

```typescript
// test/integration/events/event-bus.test.ts
describe('Redis Event Bus', () => {
  it('should publish and consume events', async () => {
    const events: any[] = []
    const consumer = new EventConsumer('stream:test', 'test-group')

    await consumer.subscribe(async (event) => {
      events.push(event)
    })

    const producer = new EventProducer()
    await producer.publish('stream:test', {
      type: 'test.event',
      payload: { data: 'hello' }
    })

    // 等待消费
    await new Promise(resolve => setTimeout(resolve, 500))

    expect(events).toHaveLength(1)
    expect(events[0].type).toBe('test.event')
    expect(events[0].payload.data).toBe('hello')
  })
})
```

### 3.4 SDK集成测试（Mock外部API）

```typescript
// test/integration/agents/claude-sdk.test.ts
import { describe, it, expect, vi } from 'vitest'
import { ClaudeAgentExecutor } from '@/services/agents/claude-executor'

describe('ClaudeAgentExecutor', () => {
  it('should execute explorer agent and return structured result', async () => {
    // Mock Claude SDK
    const mockSession = {
      run: vi.fn().mockResolvedValue({
        content: JSON.stringify({
          candidates: [
            {
              id: 'cand-1',
              title: '测试候选点',
              confidence: 0.9,
              source: { type: 'github_issue', url: 'https://...' }
            }
          ]
        })
      })
    }

    vi.mock('@anthropic-ai/agent-sdk', () => ({
      AgentSession: vi.fn().mockImplementation(() => mockSession)
    }))

    const executor = new ClaudeAgentExecutor()
    const result = await executor.executeExplorer({
      projectId: 'test-project',
      userQuery: '修复SMP问题'
    })

    expect(result.candidates).toHaveLength(1)
    expect(result.candidates[0].confidence).toBe(0.9)
    expect(mockSession.run).toHaveBeenCalledWith(
      expect.stringContaining('SMP')
    )
  })
})
```

## 4. Agent行为测试

### 4.1 决策逻辑测试

Agent的决策逻辑需要通过"Prompt + 期望输出"的方式测试：

```typescript
// test/agents/explorer-decisions.test.ts
import { describe, it, expect } from 'vitest'
import { evaluateAgentOutput } from '@/test/agent-evaluator'

describe('Explorer Agent Decision Quality', () => {
  it('should identify high-confidence candidates from mailing list data', async () => {
    const prompt = buildExplorerPrompt({
      mailingListThreads: [
        {
          subject: '[PATCH] Fix race in riscv smp_boot',
          author: 'alice@kernel.org',
          date: '2026-04-01',
          content: 'This patch fixes a known race condition...'
        },
        {
          subject: 'Re: SPI driver support for new board',
          author: 'bob@kernel.org',
          date: '2026-04-02',
          content: 'Just a question about configuration...'
        }
      ],
      githubIssues: []
    })

    const output = await runAgentWithPrompt('explorer', prompt)
    const result = evaluateAgentOutput(output, {
      schema: ExplorationResultSchema,
      assertions: [
        // 应该识别出smp_boot是更高优先级的候选
        (r) => r.candidates.some(c => 
          c.title.includes('smp_boot') && c.confidence > 0.8
        ),
        // SPI问题不应该被列为高优先级
        (r) => !r.candidates.some(c => 
          c.title.includes('SPI') && c.confidence > 0.7
        )
      ]
    })

    expect(result.passed).toBe(true)
    expect(result.score).toBeGreaterThan(0.8)
  })
})
```

### 4.2 Prompt回归测试

```typescript
// test/agents/prompt-regression.test.ts
import { describe, it, expect } from 'vitest'
import { PromptRegistry } from '@/agents/prompts'

describe('Prompt Regression Tests', () => {
  const testCases = [
    {
      name: 'explorer_basic',
      prompt: PromptRegistry.explorer,
      input: { query: 'memory management bug' },
      expectedKeywords: ['candidate', 'confidence', 'source'],
      forbiddenKeywords: ['I cannot', 'sorry', 'apologize']
    },
    {
      name: 'reviewer_security_focus',
      prompt: PromptRegistry.reviewer,
      input: { code: 'void* ptr = kmalloc(100);' },
      expectedKeywords: ['check', 'null', 'error handling'],
    }
  ]

  it.each(testCases)('$name should produce expected output', async (testCase) => {
    const output = await runPromptTest(testCase.prompt, testCase.input)

    for (const keyword of testCase.expectedKeywords) {
      expect(output.toLowerCase()).toContain(keyword)
    }

    for (const keyword of testCase.forbiddenKeywords || []) {
      expect(output.toLowerCase()).not.toContain(keyword)
    }
  })
})
```

### 4.3 Handoff集成测试

```typescript
// test/agents/handoff-integration.test.ts
describe('Agent Handoff Integration', () => {
  it('should correctly pass context from explorer to planner', async () => {
    const orchestrator = new TestOrchestrator()

    // 模拟探索阶段完成
    const explorationOutput = {
      candidates: [{
        id: 'cand-1',
        title: 'Fix smp_boot race',
        affectedFiles: ['arch/riscv/kernel/smp.c']
      }]
    }

    // 触发handoff
    const plannerInput = await orchestrator.handoff({
      from: 'explorer',
      to: 'planner',
      payload: explorationOutput
    })

    // 验证上下文传递完整性
    expect(plannerInput.selectedCandidate).toBeDefined()
    expect(plannerInput.selectedCandidate.affectedFiles).toEqual(
      explorationOutput.candidates[0].affectedFiles
    )
  })

  it('should maintain iteration context in dev-review loop', async () => {
    const orchestrator = new TestOrchestrator()

    // 第一轮开发
    const patch1 = { filesChanged: ['smp.c'], diff: '...' }
    const review1 = { decision: 'changes_requested', issues: ['missing null check'] }

    // 第二轮开发应该收到上一轮review的反馈
    const patch2 = await orchestrator.executeDeveloper({
      plan: testPlan,
      reviewFeedback: review1
    })

    // 验证开发者Agent的输出中处理了review反馈
    expect(patch2.diff).toContain('null')
  })
})
```

## 5. E2E测试

### 5.1 Playwright配置

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './test/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['junit', { outputFile: 'test-results/junit.xml' }]
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry'
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
  webServer: {
    command: 'npm run dev:test',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  }
})
```

### 5.2 关键用户旅程测试

```typescript
// test/e2e/contribution-journey.spec.ts
import { test, expect } from '@playwright/test'
import { createTestUser, createTestProject } from '@/test/e2e-helpers'

test.describe('完整贡献任务旅程', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/')
    await page.fill('[data-testid="email"]', 'test@example.com')
    await page.fill('[data-testid="password"]', 'password')
    await page.click('[data-testid="login-button"]')
    await page.waitForURL('/contributions')
  })

  test('创建Contribution并走完探索阶段', async ({ page }) => {
    // 1. 新建任务
    await page.click('[data-testid="new-contribution-button"]')
    await page.waitForURL('/contributions/new')

    await page.fill('[data-testid="title"]', '测试修复SMP竞态')
    await page.fill('[data-testid="description"]', '用户提供的描述')
    await page.selectOption('[data-testid="project"]', 'linux-riscv')
    await page.click('[data-testid="create-button"]')

    // 2. 等待进入详情页
    await page.waitForURL(/\/contributions\/[\w-]+/)
    const contributionId = page.url().split('/').pop()

    // 3. 启动探索
    await page.click('[data-testid="start-exploration-button"]')

    // 4. 等待探索完成（出现审核Gate）
    await page.waitForSelector('[data-testid="review-gate"]', { timeout: 120000 })

    // 5. 验证候选点列表存在
    const candidates = await page.locator('[data-testid="candidate-card"]')
    expect(await candidates.count()).toBeGreaterThan(0)

    // 6. 选择第一个候选点并通过审核
    await page.click('[data-testid="candidate-card"]:first-child')
    await page.fill('[data-testid="review-comment"]', '选择这个')
    await page.click('[data-testid="approve-button"]')

    // 7. 验证进入规划阶段
    await page.waitForSelector('[data-testid="stage-planning-running"]', { timeout: 60000 })
  })

  test('审核阶段拒绝并终止任务', async ({ page }) => {
    // 前置：创建并启动一个任务到探索完成
    const contribution = await setupContributionAtStage('exploration_review')
    await page.goto(`/contributions/${contribution.id}`)

    // 等待审核界面
    await page.waitForSelector('[data-testid="review-gate"]')

    // 点击拒绝
    await page.fill('[data-testid="review-comment"]', '方向不对')
    await page.click('[data-testid="reject-button"]')

    // 验证状态变为rejected
    await page.waitForSelector('[data-testid="status-rejected"]')
    const status = await page.textContent('[data-testid="status-badge"]')
    expect(status).toContain('已终止')
  })

  test('查看代码Diff并添加行级评论', async ({ page }) => {
    // 前置：创建带有Patch的任务
    const contribution = await setupContributionWithPatch()
    await page.goto(`/contributions/${contribution.id}/patches`)

    // 等待Diff加载
    await page.waitForSelector('[data-testid="diff-viewer"]')

    // 点击某一行
    await page.click('[data-testid="diff-line-42"]')
    await page.fill('[data-testid="line-comment-input"]', '这里需要加空指针检查')
    await page.click('[data-testid="submit-comment-button"]')

    // 验证评论显示
    const comment = await page.locator('[data-testid="review-comment"]').first()
    await expect(comment).toContainText('空指针检查')
  })

  test('实时日志流式显示', async ({ page }) => {
    const contribution = await setupRunningContribution()
    await page.goto(`/contributions/${contribution.id}/logs`)

    // 等待日志组件
    await page.waitForSelector('[data-testid="agent-log-stream"]')

    // 验证日志自动滚动
    const logContainer = page.locator('[data-testid="log-container"]')
    const initialScroll = await logContainer.evaluate(el => el.scrollTop)

    // 等待新日志到来
    await page.waitForTimeout(2000)
    const newScroll = await logContainer.evaluate(el => el.scrollTop)

    expect(newScroll).toBeGreaterThanOrEqual(initialScroll)
  })
})
```

## 6. 测试环境设计

### 6.1 环境架构

```mermaid
flowchart TB
    subgraph 开发环境 [开发环境<br/>Developer Local]
        D1[PostgreSQL<br/>Docker]
        D2[Redis<br/>Docker]
        D3[MinIO<br/>Docker]
        D4[Next.js Dev Server]
    end

    subgraph 测试环境 [CI测试环境<br/>Ephemeral]
        T1[Testcontainers<br/>PostgreSQL]
        T2[Testcontainers<br/>Redis]
        T3[Mock LLM Server]
    end

    subgraph 预发环境 [预发环境<br/>Staging]
        S1[PostgreSQL<br/>托管实例]
        S2[Redis<br/>托管实例]
        S3[MinIO集群]
        S4[K8s Pods]
    end

    subgraph 生产环境 [生产环境<br/>Production]
        P1[(PostgreSQL HA)]
        P2[(Redis Cluster)]
        P3[(MinIO集群)]
        P4[K8s集群]
    end
```

### 6.2 环境变量隔离

```bash
# .env.development
DATABASE_URL=postgresql://rv_insights:dev@localhost:5432/rv_insights_dev
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
OPENAI_API_KEY=sk-test-xxx    # 开发用低限额key
ANTHROPIC_API_KEY=sk-test-xxx

# .env.test (由testcontainers动态生成)
# DATABASE_URL=postgresql://test:...@localhost:random_port/test
# REDIS_URL=redis://localhost:random_port/1
# LLM_API_MOCK=true            # 测试环境默认Mock LLM调用

# .env.staging
DATABASE_URL=postgresql://.../rv_insights_staging
REDIS_URL=redis://.../staging
```

### 6.3 沙箱测试环境

Agent代码编译和测试在隔离的Docker沙箱中进行：

```dockerfile
# docker/sandbox/Dockerfile
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc-riscv64-linux-gnu \
    qemu-system-riscv \
    qemu-user-static \
    git \
    python3 \
    bc \
    bison \
    flex \
    libssl-dev \
    libncurses-dev

WORKDIR /workspace
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

## 7. CI/CD测试流水线

```mermaid
flowchart LR
    A[Push/PR] --> B[Lint & Type Check]
    B --> C[Unit Tests]
    C --> D[Integration Tests]
    D --> E[Build Docker Images]
    E --> F[E2E Tests]
    F --> G[Coverage Report]
    G --> H[Deploy Staging]

    style B fill:#fbbf24
    style C fill:#fbbf24
    style D fill:#fbbf24
    style F fill:#f87171
```

### GitHub Actions配置

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run type-check

  unit-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:unit -- --coverage
      - uses: codecov/codecov-action@v4
        with:
          files: ./coverage/lcov.info
          fail_ci_if_error: true

  integration-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:integration
        env:
          TEST_REDIS_URL: redis://localhost:6379/1

  e2e-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run test:e2e
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/

  agent-eval:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:agent
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## 8. 性能测试

### 8.1 Agent响应时间基准

```typescript
// test/performance/agent-response-time.test.ts
import { describe, it, expect } from 'vitest'

describe('Agent Response Time Benchmarks', () => {
  it('explorer agent should complete within 2 minutes', async () => {
    const start = Date.now()
    await runExplorerAgent({ query: 'SMP race condition' })
    const duration = Date.now() - start

    expect(duration).toBeLessThan(120000)
  })

  it('developer agent single iteration should complete within 5 minutes', async () => {
    const start = Date.now()
    await runDeveloperAgent({
      plan: simplePlan,
      reviewFeedback: null
    })
    const duration = Date.now() - start

    expect(duration).toBeLessThan(300000)
  })

  it('should handle 10 concurrent contributions', async () => {
    const contributions = Array.from({ length: 10 }, (_, i) => ({
      title: `并发测试 ${i}`
    }))

    const start = Date.now()
    await Promise.all(contributions.map(c => createAndStartContribution(c)))
    const duration = Date.now() - start

    expect(duration).toBeLessThan(30000) // 创建应很快
  })
})
```

### 8.2 负载测试脚本

```typescript
// test/performance/load-test.ts
import { check, sleep } from 'k6'
import http from 'k6/http'

export const options = {
  stages: [
    { duration: '2m', target: 10 },   // 预热到10用户
    { duration: '5m', target: 50 },   // 提升到50用户
    { duration: '2m', target: 100 },  // 峰值100用户
    { duration: '2m', target: 0 },    // 降温
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95%请求<2s
    http_req_failed: ['rate<0.01'],     // 错误率<1%
  }
}

export default function () {
  const res = http.get(`${__ENV.BASE_URL}/api/v1/contributions`)
  
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000
  })

  sleep(1)
}
```

## 9. 测试数据工厂

```typescript
// test/factories.ts
import { faker } from '@faker-js/faker'

export function createMockContribution(overrides = {}) {
  return {
    id: faker.string.uuid(),
    userId: faker.string.uuid(),
    projectId: faker.string.uuid(),
    title: faker.lorem.sentence(),
    description: faker.lorem.paragraph(),
    status: 'draft',
    currentStage: null,
    config: { maxIterations: 5, autoApproveThreshold: 0.85 },
    createdAt: faker.date.recent(),
    updatedAt: faker.date.recent(),
    ...overrides
  }
}

export function createMockStageExecution(overrides = {}) {
  return {
    id: faker.string.uuid(),
    contributionId: faker.string.uuid(),
    stageType: 'exploration',
    status: 'pending',
    iteration: 0,
    input: {},
    output: null,
    startedAt: faker.date.recent(),
    completedAt: null,
    errorLog: null,
    ...overrides
  }
}

export function createMockPatch(overrides = {}) {
  return {
    id: faker.string.uuid(),
    contributionId: faker.string.uuid(),
    stageExecutionId: faker.string.uuid(),
    iteration: 1,
    diffContent: `diff --git a/test.c b/test.c\n@@ -1 +1 @@\n-old\n+new`,
    commitMessage: faker.git.commitMessage(),
    filesChanged: ['test.c'],
    status: 'pending_review',
    createdAt: faker.date.recent(),
    ...overrides
  }
}

export function createMockReviewResult(overrides = {}) {
  return {
    decision: 'changes_requested',
    overallScore: 0.6,
    dimensions: {
      correctness: { score: 0.7, issues: [] },
      security: { score: 0.5, issues: [] },
      performance: { score: 0.8, issues: [] },
      styleCompliance: { score: 0.9, issues: [] },
      riscvSpecific: { score: 0.4, issues: [] },
      testCoverage: { score: 0.6, issues: [] }
    },
    summary: faker.lorem.sentence(),
    issues: [{
      severity: 'high',
      file: 'arch/riscv/kernel/smp.c',
      lineNumber: 42,
      category: 'race-condition',
      description: 'Potential race condition detected',
      suggestion: 'Add spin_lock protection'
    }],
    ...overrides
  }
}
```

## 10. 测试质量门禁

```typescript
// test/quality-gate.ts
export const qualityGate = {
  // 覆盖率要求
  coverage: {
    lines: 85,
    functions: 85,
    branches: 80,
    statements: 85
  },

  // Agent测试要求
  agentTests: {
    explorerAccuracy: 0.8,        // 候选点识别准确率
    reviewerPrecision: 0.85,      // 审核问题检出率
    plannerCompleteness: 0.9      // 规划方案完整度
  },

  // 性能要求
  performance: {
    apiP95: 2000,                 // ms
    explorerMaxDuration: 120000,  // ms
    developerMaxDuration: 300000  // ms
  },

  // E2E要求
  e2e: {
    criticalPathPassRate: 100     // 关键用户旅程必须100%通过
  }
}
```
