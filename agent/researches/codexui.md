# CodexUI 项目深度分析文档

> 生成时间: 2026-05-03
> 分析路径: `/Users/zq/Desktop/ai-projs/posp/template/codexUI`
> 版本: v0.1.87
> 最新提交: 08c14db Merge pull request #115 from friuns2/codex/skills-tab-npx-find

---

## 1. 项目概述

**CodexUI**（npm包名: `codexapp`）是一个基于浏览器的 Codex AI 编程助手 Web 界面。它将 OpenAI Codex 桌面应用的功能暴露为跨平台的 Web UI，允许用户通过任何浏览器访问 Codex 的功能，支持 Linux、Windows、macOS 和 Android (Termux)。

### 核心定位
- **桥接层**: 在浏览器和 Codex app-server 之间建立通信桥梁
- **跨平台**: 消除对桌面环境的依赖，支持服务器/ headless 场景
- **单命令启动**: `npx codexapp` 即可运行完整服务
- **远程访问**: 内置 Cloudflare Tunnel、Tailscale 支持

### 主要功能
- 💬 线程式对话管理（创建、归档、分支、回滚）
- 🔄 实时流式响应（WebSocket + SSE 双通道）
- 🗂️ 按项目组织线程
- 🖥️ 集成终端（每个线程一个 xterm.js 终端）
- 📁 本地文件浏览和编辑
- 🔌 多提供商支持（OpenAI Codex、OpenRouter、OpenCode Zen、自定义端点）
- 🤖 Skills/插件系统（Composio、MCP、GitHub Skills）
- 📱 移动端适配（PWA、响应式布局）
- 🎙️ 语音输入（语音转文字）
- 📊 Git 代码审查（diff 查看、暂存/撤销）
- 🤖 Telegram Bot 桥接
- 🔐 密码保护和会话管理

---

## 2. 架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        浏览器层 (Browser)                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Vue 3 SPA (Composition API, <script setup>)                 │  │
│  │  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐     │  │
│  │  │ App.vue     │  │ Composables  │  │ API Layer        │     │  │
│  │  │ (5,073行)   │──│ useDesktop   │──│ codexGateway     │     │  │
│  │  │             │  │ State        │  │ codexRpcClient   │     │  │
│  │  └────────────┘  └──────────────┘  └────────┬─────────┘     │  │
│  └─────────────────────────────────────────────┼───────────────┘  │
└────────────────────────────────────────────────┼──────────────────┘
                                                 │ HTTP / WebSocket
┌────────────────────────────────────────────────┼──────────────────┐
│                   Node.js 服务器层 (Server)                          │
│  ┌─────────────────────────────────────────────┼───────────────┐  │
│  │ Express / Vite Middleware                   │               │  │
│  │  ┌───────────────────┐  ┌─────────────┬─────┴───────────┐  │  │
│  │  │ Auth Middleware    │  │ Codex Bridge│ Local Routes    │  │  │
│  │  │ (password, cookie) │  │ /codex-api/*│ /codex-local-*  │  │  │
│  │  └───────────────────┘  └─────────────┴─────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                    │ stdin/stdout                  │
│  ┌─────────────────────────────────┼────────────────────────────┐ │
│  │ codex app-server (子进程)       │                            │ │
│  │ JSON-RPC over newline-delimited I/O                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

### 架构特点
1. **无状态桥接**: 服务器本身不存储业务状态，所有状态在 Codex app-server 中
2. **单例桥接器**: 一个 Node 进程管理一个 Codex app-server 子进程
3. **实时双通道**: WebSocket 优先，SSE 自动降级
4. **双构建输出**: Vite 构建前端 SPA，tsup 构建 CLI

---

## 3. 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **前端框架** | Vue 3 | ^3.5.13 | UI 框架，Composition API |
| **路由** | Vue Router 4 | ^4.6.4 | 客户端路由 |
| **构建工具** | Vite 6 | ^6.1.0 | 开发服务器和前端构建 |
| **样式** | Tailwind CSS 4 | ^4.1.18 | 原子化 CSS |
| **类型检查** | TypeScript 5 | ^5.7.3 | 类型系统 |
| **Vue SFC 编译** | vue-tsc | ^2.2.0 | Vue 单文件组件类型检查 |
| **CLI 构建** | tsup 8 | ^8.4.0 | Node.js CLI 打包 |
| **服务器** | Express 5 | ^5.1.0 | 生产环境 HTTP 服务器 |
| **CLI 框架** | Commander 13 | ^13.1.0 | 命令行参数解析 |
| **实时通信** | WebSocket (ws) | ^8.18.3 | 服务器推送 |
| **终端模拟** | xterm.js + node-pty | ^6.0.0 / ^1.1.0 | 浏览器内终端 |
| **语法高亮** | highlight.js | ^11.11.1 | 代码块高亮 |
| **测试框架** | Vitest 4 | ^4.1.5 | 单元测试 |
| **E2E 测试** | Playwright | ^1.59.1 | 端到端测试 |
| **运行时** | Node.js | >= 18 | 服务器运行时 |

---

## 4. 目录结构

```
codexUI/
├── src/                              # 源代码
│   ├── api/                          # API 通信层
│   │   ├── codexGateway.ts           # 高层 API 封装 (3,082 行)
│   │   ├── codexRpcClient.ts         # 底层 RPC 传输 (366 行)
│   │   ├── codexErrors.ts            # 错误处理 (68 行)
│   │   ├── appServerDtos.ts          # DTO 类型定义
│   │   └── normalizers/
│   │       └── v2.ts                 # API 响应标准化 (627 行)
│   ├── components/                   # Vue 组件
│   │   ├── content/                  # 内容区域组件 (21 个文件)
│   │   ├── icons/                    # Tabler 图标组件 (24 个)
│   │   ├── layout/                   # 布局组件
│   │   └── sidebar/                  # 侧边栏组件
│   ├── composables/                  # Vue 组合式函数
│   │   ├── useDesktopState.ts        # 核心状态管理 (5,341 行)
│   │   ├── useDictation.ts           # 语音输入
│   │   ├── useGithubSkillsSync.ts    # GitHub Skills 同步
│   │   ├── useMobile.ts              # 移动端检测
│   │   └── useUiLanguage.ts          # 国际化 (中英)
│   ├── server/                       # Node.js 服务器代码
│   │   ├── codexAppServerBridge.ts   # 核心桥接器 (6,402 行)
│   │   ├── httpServer.ts             # Express 服务器 (287 行)
│   │   ├── authMiddleware.ts         # 认证中间件
│   │   ├── password.ts               # 密码生成
│   │   ├── localBrowseUi.ts          # 本地文件浏览/编辑
│   │   ├── terminalManager.ts        # 终端会话管理 (498 行)
│   │   ├── telegramThreadBridge.ts   # Telegram 桥接 (765 行)
│   │   ├── accountRoutes.ts          # 账户管理路由
│   │   ├── skillsRoutes.ts           # Skills 路由
│   │   ├── reviewGit.ts              # Git 审查路由
│   │   ├── freeMode.ts               # 免费模式管理
│   │   ├── openRouterProxy.ts        # OpenRouter 代理
│   │   ├── zenProxy.ts               # OpenCode Zen 代理
│   │   ├── customEndpointProxy.ts    # 自定义端点代理
│   │   ├── unifiedResponsesProxy.ts  # 统一响应代理
│   │   └── appServerRuntimeConfig.ts # 运行时配置
│   ├── cli/                          # CLI 入口
│   │   └── index.ts                  # Commander CLI (680 行)
│   ├── types/
│   │   └── codex.ts                  # UI 层 TypeScript 类型 (330 行)
│   ├── router/
│   │   └── index.ts                  # Vue Router 配置
│   ├── utils/
│   │   └── commandInvocation.ts      # 命令调用工具
│   ├── pathUtils.ts                  # 路径处理工具
│   ├── commandResolution.ts          # 命令解析工具
│   ├── App.vue                       # 根组件 (5,073 行)
│   ├── main.ts                       # Vue 应用入口
│   └── style.css                     # 全局样式 (1,532 行)
├── documentation/                    # Codex app-server 协议文档
│   ├── APP_SERVER_DOCUMENTATION.md   # 完整协议参考
│   └── app-server-schemas/           # JSON + TypeScript Schema
│       ├── json/                     # JSON Schema (v1, v2)
│       └── typescript/               # TypeScript 类型定义
├── scripts/                          # 脚本工具
│   ├── dev.cjs                       # 开发服务器启动器
│   ├── fix-pty-native-build.cjs      # node-pty 原生构建修复
│   └── profile-browser-runtime.cjs   # 浏览器性能分析
├── test/                             # 测试资源
│   └── fixtures/                     # 测试夹具
├── public/                           # 静态资源
│   ├── icons/                        # PWA 图标
│   ├── manifest.webmanifest          # PWA 配置
│   └── sw.js                         # Service Worker
├── index.html                        # SPA 入口
├── vite.config.ts                    # Vite 配置
├── vite.config.https.ts              # HTTPS Vite 配置
├── tsup.config.ts                    # CLI 构建配置
├── vitest.config.ts                  # 测试配置
├── tsconfig.json                     # 前端 TS 配置
├── tsconfig.node.json                # Node 工具 TS 配置
├── tsconfig.server.json              # 服务器 TS 配置
├── package.json                      # 包配置
├── tests.md                          # 测试文档 (203KB)
├── PROJECT_SPEC.md                   # 项目规范
├── ProxySpec.md                      # 代理规范
├── AGENTS.md                         # 代理工作流规范
├── README.md                         # 项目说明
└── llm-wiki/                         # LLM 知识库
    ├── raw/                          # 原始笔记
    └── wiki/                         # 综合文档
```

---

## 5. 前端架构详解

### 5.1 应用入口

**`src/main.ts`** (17 行) - 极简入口:
```typescript
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import { t } from './composables/useUiLanguage'

createApp(App).use(router).mount('#app')

// PWA Service Worker 注册
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  navigator.serviceWorker.register('/sw.js')
}
```

### 5.2 路由系统

**`src/router/index.ts`** - 哈希模式路由:

| 路由 | 路径 | 说明 |
|------|------|------|
| home | `/` | 新建线程/文件夹选择器 |
| thread | `/thread/:threadId` | 线程对话视图 |
| skills | `/skills` | Skills/插件中心 |
| new-thread | `/new-thread` | 重定向到 home |
| fallback | `/*` | 重定向到 home |

**关键设计**: 所有路由使用 `EmptyRouteView`（渲染 null），实际内容由 `App.vue` 根据 `route.name` 条件渲染。这是一种非传统的单页面架构。

### 5.3 组件架构

#### 5.3.1 组件层次结构

```
App.vue (根组件, 5,073 行)
├── DesktopLayout.vue (布局)
│   ├── #sidebar (插槽)
│   │   ├── SidebarThreadControls.vue (工具栏)
│   │   ├── SidebarThreadTree.vue (线程树)
│   │   └── 设置面板 (内联)
│   └── #content (插槽)
│       ├── ContentHeader.vue (标题栏)
│       ├── ThreadConversation.vue (消息列表)
│       ├── ThreadComposer.vue (输入框)
│       ├── ThreadTerminalPanel.vue (终端)
│       ├── ThreadPendingRequestPanel.vue (审批请求)
│       ├── QueuedMessages.vue (排队消息)
│       ├── ReviewPane.vue (Git 审查)
│       ├── SkillsHub.vue (Skills 中心)
│       └── DirectoryHub.vue (插件目录)
└── Codex 登录模态框
```

#### 5.3.2 组件分类统计

| 类别 | 数量 | 说明 |
|------|------|------|
| Content 组件 | 19 | 核心功能组件 |
| Icon 组件 | 24 | Tabler 图标 SVG |
| Layout 组件 | 1 | 桌面布局 |
| Sidebar 组件 | 4 | 侧边栏相关 |

#### 5.3.3 关键组件职责

**`App.vue`** (5,073 行) - 应用壳:
- 整合所有状态（useDesktopState, useMobile）
- 管理侧边栏折叠/展开
- 处理线程选择、创建、归档
- 管理设置面板（账户、主题、语言、提供商）
- 处理新项目创建流程
- 管理语音输入、终端、审查面板

**`ThreadConversation.vue`** - 消息渲染器:
- 支持用户/助手/系统消息
- Markdown 渲染（标题、列表、代码块、表格）
- 文件变更展示（add/update/delete/move）
- 代码执行状态显示
- 计划步骤展示
- 实时覆盖层（思考文本、活动标签）

**`ThreadComposer.vue`** - 输入组件:
- 多行文本输入
- 模型选择下拉框
- 推理力度选择
- 速度模式切换
- Skills 选择器
- 文件附件（拖放支持）
- 语音输入按钮
- 发送/停止按钮

**`DesktopLayout.vue`** - 布局组件:
- 桌面端: 可调整侧边栏宽度（260-620px）
- 移动端: 抽屉式覆盖层
- 响应式断点: 768px

### 5.4 状态管理

**无 Pinia/Vuex**，使用纯 Composition API:

#### 5.4.1 useDesktopState (5,341 行)

核心状态组合式函数，管理所有应用状态:

**主要状态**:
```typescript
// 线程状态
projectGroups: UiProjectGroup[]          // 按项目分组的线程
selectedThreadId: string                 // 当前选中的线程
isLoadingThreads: boolean                // 线程加载中

// 消息状态
persistedMessagesByThreadId: Record<string, UiMessage[]>  // 已加载的消息
liveAgentMessagesByThreadId: Record<string, string>        // 流式消息
liveReasoningTextByThreadId: Record<string, string>        // 流式推理文本

// 进行状态
inProgressById: Record<string, boolean>  // 各线程是否进行中
pendingServerRequestsByThreadId: Record<string, UiServerRequest[]>  // 待审批请求

// 配置状态
availableModelIds: string[]               // 可用模型列表
selectedModelId: string                   // 选中的模型
selectedReasoningEffort: ReasoningEffort  // 推理力度
selectedSpeedMode: SpeedMode             // 速度模式
selectedCollaborationMode: CollaborationModeKind  // 协作模式

// UI 状态
isSidebarCollapsed: boolean              // 侧边栏折叠
isSettingsOpen: boolean                  // 设置面板打开
sendWithEnter: boolean                   // Enter 发送
darkMode: 'system' | 'dark' | 'light'    // 主题模式
uiLanguage: 'en' | 'zh-CN'              // 界面语言
```

**持久化存储** (localStorage):
| 键 | 数据 |
|----|------|
| `codex-web-local.thread-read-state.v1` | 线程已读时间戳 |
| `codex-web-local.selected-thread-id.v1` | 最后选中的线程 |
| `codex-web-local.project-order.v1` | 自定义项目排序 |
| `codex-web-local.project-display-name.v1` | 自定义项目名称 |
| `codex-web-local.auto-refresh-enabled.v1` | 自动刷新开关 |
| `codex-web-local.sidebar-collapsed.v1` | 侧边栏折叠状态 |
| `codex-web-local.selected-model-by-context.v1` | 按上下文保存的模型 |
| `codex-web-local.collaboration-mode-by-context.v1` | 按上下文保存的协作模式 |

#### 5.4.2 其他 Composables

| Composable | 行数 | 功能 |
|------------|------|------|
| `useDictation` | 307 | 语音录制、波形可视化、服务器转录 |
| `useGithubSkillsSync` | 246 | GitHub 设备流 OAuth、Skills 同步 |
| `useMobile` | 25 | 响应式移动端检测 (768px) |
| `useUiLanguage` | 459 | 国际化，支持中英文 |

### 5.5 样式系统

#### 5.5.1 Tailwind CSS v4

- **构建方式**: `@tailwindcss/vite` 插件（非 PostCSS）
- **全局样式**: `src/style.css` (1,532 行)
- **组件样式**: `<style scoped>` 配合 `@reference "tailwindcss"`

#### 5.5.2 主题策略

**暗色主题**:
- 基于 class 切换（`:root.dark`）
- 全局覆盖约 1,400 行暗色样式
- 颜色方案: `zinc-*` 为主，`emerald`（成功）、`sky`（链接）、`amber`（警告）、`rose`（错误）为强调色

**亮色主题**:
- 使用 `slate-*` 颜色
- 暗色覆盖通过 `:root.dark` 选择器实现

#### 5.5.3 移动端适配

- 响应式断点: 768px
- 输入框强制 `font-size: 16px` 防止 iOS 缩放
- PWA 支持: manifest、Service Worker、Apple 触摸图标

---

## 6. 后端架构详解

### 6.1 服务器架构

#### 6.1.1 HTTP 服务器 (`src/server/httpServer.ts`)

Express 应用工厂模式:

**中间件链** (按顺序):
1. **认证中间件** (条件) - 基于密码的会话保护
2. **本地图片服务** (`/codex-local-image`) - 流式传输本地图片
3. **本地文件服务** (`/codex-local-file`) - 内联文件显示
4. **目录列表 JSON** (`/codex-local-directories`) - 文件夹选择器数据
5. **目录浏览 UI** (`/codex-local-browse/*`) - HTML 目录浏览器
6. **文本编辑器** (`/codex-local-edit/*`) - GET 渲染编辑器，PUT 保存文件
7. **Codex 桥接** (`/codex-api/*`) - 核心 API 代理
8. **静态文件服务** (`dist/`) - Vue 构建产物
9. **SPA 回退** - 所有路由返回 `index.html`

**WebSocket 服务器**:
- 路径: `/codex-api/ws`
- noServer 模式，手动处理 HTTP upgrade
- 认证在 upgrade 阶段检查

#### 6.1.2 认证与安全 (`src/server/authMiddleware.ts`)

**多层认证策略**:

| 层级 | 机制 | 说明 |
|------|------|------|
| 本地绕过 | IP 白名单 | 127.0.0.1/::1 + localhost Host |
| Tailscale 绕过 | IP 范围 | 100.64-127.x.x 或 fd7a: 前缀 |
| 会话 Cookie | HttpOnly | `portal_session`，30 天 TTL |
| 密码比较 | 恒定时间 | `crypto.timingSafeEqual` 防时序攻击 |
| 一键认证 | URL 参数 | `/password=<value>` 自动设置 Cookie |

**会话存储**:
- 文件: `~/.codex/webui-auth-sessions.json`
- 原子写入（临时文件 + 重命名）
- 最多 128 个令牌，自动清理过期会话

### 6.2 核心桥接器 (`src/server/codexAppServerBridge.ts`)

6,402 行，项目的核心。

#### 6.2.1 进程管理

```
Node.js 进程
  └─ spawn("codex app-server")
       ├─ stdin ← JSON-RPC 请求
       └─ stdout → JSON-RPC 响应/通知
```

- JSON-RPC 2.0 over stdio
- 自动重启崩溃的子进程
- `initialize`/`initialized` 握手

#### 6.2.2 请求路由

**RPC 代理** (通过 `codex app-server`):
- `thread/list`, `thread/read`, `thread/start`, `thread/resume`
- `turn/start`, `turn/interrupt`
- `model/list`, `config/read`, `config/write`
- `skills/list`, `plugin/list`, `app/list`

**自定义路由** (Express 直接处理):

| 路由前缀 | 处理文件 | 功能 |
|----------|----------|------|
| `/codex-api/accounts/*` | `accountRoutes.ts` | 账户管理 |
| `/codex-api/skills-hub/*` | `skillsRoutes.ts` | Skills 系统 |
| `/codex-api/review/*` | `reviewGit.ts` | Git 审查 |
| `/codex-api/openrouter-proxy/*` | `openRouterProxy.ts` | OpenRouter 代理 |
| `/codex-api/zen-proxy/*` | `zenProxy.ts` | OpenCode Zen 代理 |
| `/codex-api/custom-proxy/*` | `customEndpointProxy.ts` | 自定义端点 |
| `/codex-api/terminal/*` | `terminalManager.ts` | 终端管理 |
| `/codex-api/composio/*` | 内联 | Composio 集成 |
| `/codex-api/telegram/*` | 内联 | Telegram 配置 |

#### 6.2.3 内联载荷处理

- 检测 base64 编码图片
- 持久化到 `/tmp/codex-web-inline-media/`
- SHA1 文件名，替换为代理 URL

#### 6.2.4 会话日志恢复

- 解析 `apply_patch` 工具调用
- 解析 `exec_command` 函数调用
- 反向应用补丁实现回滚

### 6.3 CLI 入口 (`src/cli/index.ts`)

680 行，基于 Commander 的 CLI。

**主要功能**:
- 自动安装 Codex CLI（Termux 使用特殊包）
- 自动检测 Tailscale IP，决定是否启动 Cloudflare Tunnel
- 端口回退（端口被占用时自动递增）
- 绑定 `0.0.0.0` 支持 LAN 访问
- 生成并显示二维码
- 持久化启动项目到 Codex 全局状态

**命令选项**:
```
codexapp [options]
  --port <number>          端口 (默认 5900)
  --password <string>      密码
  --no-password           禁用密码
  --tunnel                启用 Cloudflare Tunnel
  --no-tunnel             禁用 Tunnel
  --open                  自动打开浏览器
  --no-open               不打开浏览器
  --login                 启动时运行 codex login
  --no-login              跳过登录
  --sandbox-mode <mode>   沙盒模式
  --approval-policy <policy> 审批策略
```

### 6.4 终端管理 (`src/server/terminalManager.ts`)

498 行，基于 `node-pty` 的终端会话管理。

**功能**:
- 每线程一个 PTY 会话
- 16KB 滚动缓冲区
- 跨平台 shell 解析（Unix: `$SHELL`，Windows: `%COMSPEC%`）
- 本地环境规范化（`LANG=en_US.UTF-8`）
- 快速命令发现（package.json scripts、Makefile、scripts/ 目录）

### 6.5 本地文件系统 (`src/server/localBrowseUi.ts`)

**功能**:
- 目录列表（按修改时间排序，目录在前）
- HTML 文件浏览器（暗色主题）
- Ace 编辑器集成（CDN 加载）
- 30+ 已知文本扩展名 + 二进制探测
- 10MB 写入限制

---

## 7. 数据流与通信协议

### 7.1 通信架构

```
浏览器                          Express 服务器                 Codex app-server
  │                                │                              │
  ├─ POST /codex-api/rpc ───────→ ├─ 写入 stdin ───────────────→ │
  │  { method, params }            │  { jsonrpc, id, method }     │
  │                                │                              │
  │ ←──────────────────────────── ├─ 读取 stdout ──────────────── │
  │  { result }                    │  { id, result }              │
  │                                │                              │
  ├─ WS /codex-api/ws ──────────→ ├─ 订阅通知 ←────────────────── │
  │  { method, params }            │  { method, params }          │
  │                                │                              │
```

### 7.2 RPC 客户端层

#### 7.2.1 传输层 (`src/api/codexRpcClient.ts`)

**HTTP RPC**:
- `POST /codex-api/rpc`
- 请求: `{ method, params }`
- 响应: `{ result: T }`

**实时通知**:
1. **WebSocket** (优先):
   - 路径: `/codex-api/ws`
   - 连接时发送 `{ method: 'ready', params: { ok: true } }`
   - 指数退避重连: `min(1000 * 2^attempt, 10000)ms`
   - 2.5 秒降级计时器

2. **SSE** (降级):
   - 路径: `/codex-api/events`
   - 命名事件 `ready`
   - 相同指数退避策略

#### 7.2.2 API 网关 (`src/api/codexGateway.ts`)

80+ 个导出函数，分类:

| 类别 | 函数示例 |
|------|----------|
| 线程 CRUD | `getThreadGroups`, `startThread`, `forkThread`, `archiveThread` |
| 消息/回合 | `startThreadTurn`, `interruptThreadTurn` |
| 模型配置 | `getAvailableModelIds`, `setDefaultModel`, `setCodexSpeedMode` |
| 终端 | `attachThreadTerminal`, `sendThreadTerminalInput` |
| 账户 | `getAccounts`, `switchAccount`, `startCodexLogin` |
| 审查 | `getReviewSnapshot`, `applyReviewAction` |
| 目录/插件 | `getPluginsList`, `installPlugin`, `getComposioConnectors` |
| Skills | `getSkillsList`, `installSkill`, `enableSkill` |
| 文件系统 | `listLocalDirectories`, `createLocalDirectory` |
| Telegram | `configureTelegramBot`, `getTelegramStatus` |
| 提供商 | `setFreeMode`, `setFreeModeCustomKey`, `setCustomProvider` |

### 7.3 标准化层 (`src/api/normalizers/v2.ts`)

**线程分组**:
- `normalizeThreadGroupsV2`: `ThreadListResponse` → `UiProjectGroup[]`
- 按 CWD 叶子名称分组

**消息标准化**:
- `normalizeThreadMessagesV2`: 将 turns/items 扁平化为 `UiMessage[]`
- 处理 8 种 item 类型: agentMessage, userMessage, imageView, imageGeneration, reasoning, plan, commandExecution, fileChange

**文件变更**:
- `toUiFileChanges`: 提取文件 diff
- `normalizeFileChangeStatus`: 标准化变更状态

### 7.4 错误处理 (`src/api/codexErrors.ts`)

**CodexApiError 类**:
```typescript
class CodexApiError extends Error {
  code: 'http_error' | 'rpc_error' | 'network_error' | 'invalid_response' | 'unknown_error'
  method?: string
  status?: number
}
```

**错误提取策略** (6 层回退):
1. 直接字符串
2. `payload.error` (字符串)
3. `payload.error.message`
4. `payload.message`
5. `payload.detail`
6. 默认字符串

---

## 8. 外部集成

### 8.1 AI 提供商代理

#### 8.1.1 OpenRouter (`openRouterProxy.ts`)
- 端点: `https://openrouter.ai/api/v1/responses`
- 工具类型过滤（只允许 `function` 和 `openrouter:*`）
- 支持 chat 到 responses 的降级

#### 8.1.2 OpenCode Zen (`zenProxy.ts`)
- 端点: `https://opencode.ai/zen/v1/responses`
- 强制 chat 格式 (`responsesPayloadFormat: 'chat'`)
- 无工具降级

#### 8.1.3 自定义端点 (`customEndpointProxy.ts`)
- 用户可配置 base URL
- 自动附加 `/responses` 或 `/chat/completions`

#### 8.1.4 统一代理引擎 (`unifiedResponsesProxy.ts`)
- Responses API ↔ Chat Completions 双向翻译
- `responsesInputToMessages()`: 转换 input 为 ChatMessage
- `chatCompletionToResponsesFormat()`: 包装 chat 响应
- SSE 流式转换

### 8.2 免费模式 (`src/server/freeMode.ts`)

- 约 65 个 XOR 加密的 OpenRouter API 密钥
- 10 分钟缓存的免费模型发现
- 三种提供商类型: OpenRouter（默认免费）、自定义、OpenCode Zen
- 状态持久化: `~/.codex/webui-free-mode.json`

### 8.3 Telegram 桥接 (`src/server/telegramThreadBridge.ts`)

765 行，完整的 Telegram Bot 集成。

**功能**:
- 长轮询（45 秒超时）
- 用户白名单（`TELEGRAM_ALLOWED_USER_IDS`）
- Bot 命令:
  - `/start` - 快速开始
  - `/threads` - 列出线程
  - `/newthread` - 创建新线程
  - `/thread <id>` - 连接现有线程
  - `/current` - 显示当前线程
  - `/history` - 显示历史
  - `/status` - 状态
  - `/whoami` - 用户信息
  - `/help` - 帮助
- Markdown → Telegram HTML 渲染
- 自动分块（3500 字符）

### 8.4 GitHub Skills 同步

- GitHub 设备流 OAuth
- 私有 fork: `OpenClawAndroid/skills`
- Git 工作树同步（基于 mtime 的冲突解决）
- Skills 搜索: `npx skills find`
- 安装/卸载: Python 安装脚本或 git clone

### 8.5 Composio 集成

- CLI 包装器（`composio` 二进制）
- 命令: `whoami`, `connections list`, `tools list`, `link`, `login`
- OAuth 链接流
- 状态读取: `~/.composio/user_data.json`

### 8.6 Firebase/OpenAI 认证

- 读取 `~/.codex/auth.json`
- Token 刷新: `https://auth.openai.com/oauth/token`
- JWT 解码提取 email/plan
- 多账户管理: `~/.codex/accounts/<sha256>/auth.json`

---

## 9. 构建系统

### 9.1 双构建输出

```
源代码
  ├─ Vite 构建 ──→ dist/ (前端 SPA)
  │   • Vue SFC 编译
  │   • Tailwind CSS 处理
  │   • TypeScript 转译
  │   • 资源优化
  │
  └─ tsup 构建 ──→ dist-cli/ (Node.js CLI)
      • ESM 输出
      • Node 18 目标
      • 外部依赖: express, commander
      • shebang: #!/usr/bin/env node
```

### 9.2 开发工作流

**开发模式** (`pnpm run dev`):
```
scripts/dev.cjs
  ├─ Android/Termux 检测 → 构建 CLI + 生产服务器
  ├─ 检查 vite/vue-tsc → 自动 pnpm install
  └─ 委托给 Vite (port 5173)
      └─ codex-bridge 插件
          ├─ WebSocket 服务器
          ├─ 本地文件中间件
          └─ Codex 桥接中间件
```

**生产模式** (`npx codexapp`):
```
dist-cli/index.js (CLI)
  ├─ 自动安装 Codex CLI
  ├─ 创建 Express 服务器
  ├─ 提供 dist/ 静态文件
  ├─ 挂载桥接中间件
  ├─ 可选: Cloudflare Tunnel
  └─ 默认端口: 5900
```

### 9.3 配置文件

| 文件 | 用途 |
|------|------|
| `vite.config.ts` | Vite 主配置（Vue + Tailwind + 桥接插件） |
| `vite.config.https.ts` | HTTPS 开发配置 |
| `tsup.config.ts` | CLI 打包配置 |
| `vitest.config.ts` | 测试配置 |
| `tsconfig.json` | 前端 TS（ES2020, DOM 类型） |
| `tsconfig.node.json` | Vite 工具 TS |
| `tsconfig.server.json` | 服务器 TS（ES2022, Node 类型） |

---

## 10. 测试策略

### 10.1 测试文件 (6 个)

| 文件 | 行数 | 测试内容 |
|------|------|----------|
| `useDesktopState.test.ts` | - | 状态管理逻辑 |
| `codexAppServerBridge.inlinePayload.test.ts` | - | 内联载荷处理 |
| `codexAppServerBridge.authRefresh.test.ts` | - | 认证刷新 |
| `terminalManager.test.ts` | - | 终端管理 |
| `directoryHubUtils.test.ts` | - | 目录工具 |
| `codexGateway.test.ts` | - | API 网关 |

### 10.2 测试运行

```bash
pnpm run test:unit    # vitest run
```

### 10.3 E2E 测试

- Playwright 用于浏览器性能分析 (`scripts/profile-browser-runtime.cjs`)
- 拦截 `/codex-api` 请求，测量时延和大小
- 生成 JSON 报告 + 截图 + Playwright trace

---

## 11. 关键设计决策

### 11.1 无状态管理库

**决策**: 不使用 Pinia/Vuex，所有状态集中在 `useDesktopState` 组合式函数中。

**原因**:
- 单一组合式函数足够管理整个应用状态
- 避免引入额外依赖
- 状态与组件解耦

**代价**:
- `useDesktopState.ts` 达到 5,341 行
- `App.vue` 达到 5,073 行
- 可维护性挑战

### 11.2 无路由视图组件

**决策**: 路由只改变 URL，所有视图渲染在 `App.vue` 中通过 `v-if` 控制。

**原因**:
- 状态全部在 `useDesktopState`，无需路由级状态分离
- 避免复杂的跨路由状态同步
- 实时更新需要全局状态监听

### 11.3 桥接而非重写

**决策**: 不实现 AI 逻辑，全部代理给 Codex app-server。

**原因**:
- 复用 Codex 桌面版的全部功能
- 自动获得新功能（当 Codex 更新时）
- 减少维护负担

### 11.4 实时双通道

**决策**: WebSocket 优先，SSE 自动降级。

**原因**:
- WebSocket 延迟更低
- SSE 作为可靠降级（防火墙友好）
- 自动重连和退避

### 11.5 暗色主题全局覆盖

**决策**: 暗色主题覆盖集中在 `style.css`，而非组件级。

**原因**:
- 统一管理主题
- 避免组件间样式冲突
- 符合项目规范（AGENTS.md）

---

## 12. 安全机制

### 12.1 认证
- 密码自动生成（`xxx-xxx-xxx` 格式）
- 恒定时间密码比较
- HttpOnly Cookie
- 本地/Tailscale 自动绕过

### 12.2 会话
- 30 天 TTL
- 文件持久化（原子写入）
- 最多 128 个活跃会话

### 12.3 文件访问
- 只允许绝对路径
- 文本文件编辑限制（扩展名白名单 + 二进制探测）
- 10MB 写入限制

### 12.4 输入处理
- 路径规范化（Windows `\\?\` 处理）
- 防御性标准化（`asRecord()`, `readString()`）

---

## 13. 性能优化

### 13.1 前端
- **引用相等优化**: 消息合并使用身份检查避免不必要的重渲染
- **防抖同步**: 事件驱动同步 220ms 防抖
- **虚拟滚动**: 大列表优化
- **按需加载**: 组件级懒加载

### 13.2 后端
- **内联图片提取**: base64 → 文件，减少传输
- **回合修剪**: 限制返回最近 10 个回合
- **模型缓存**: 免费模型 10 分钟缓存
- **API 性能日志**: 可选的时延和大小监控

---

## 14. 项目统计

### 14.1 代码规模

| 文件/目录 | 行数 | 说明 |
|-----------|------|------|
| `src/App.vue` | 5,073 | 根组件 |
| `src/composables/useDesktopState.ts` | 5,341 | 状态管理 |
| `src/server/codexAppServerBridge.ts` | 6,402 | 核心桥接器 |
| `src/api/codexGateway.ts` | 3,082 | API 网关 |
| `src/style.css` | 1,532 | 全局样式 |
| `src/types/codex.ts` | 330 | 类型定义 |
| `src/cli/index.ts` | 680 | CLI 入口 |
| `src/router/index.ts` | 33 | 路由配置 |
| `src/main.ts` | 17 | 应用入口 |
| **总计 (src/)** | **~25,000+** | **全部源码** |

### 14.2 依赖统计

| 类型 | 数量 |
|------|------|
| 运行时依赖 | 10 |
| 开发依赖 | 15 |

### 14.3 Git 活动

- **总提交数**: ~1,305（自 2025-04-01）
- **分支数**: 50+（含远程）
- **最新提交**: `08c14db` - Merge PR #115

---

## 15. 开发指南

### 15.1 快速开始

```bash
# 安装依赖
pnpm install

# 开发模式
pnpm run dev

# 构建
pnpm run build

# 测试
pnpm run test:unit

# 预览生产构建
pnpm run preview
```

### 15.2 添加新功能

1. **添加 API 调用**: 在 `src/api/codexGateway.ts` 中添加函数
2. **添加状态**: 在 `src/composables/useDesktopState.ts` 中添加 ref
3. **添加 UI**: 在 `src/components/content/` 创建组件，在 `App.vue` 中使用
4. **添加路由**: 在 `src/router/index.ts` 添加路由（如需要）
5. **添加样式**: 在 `src/style.css` 添加暗色主题覆盖
6. **更新测试**: 在 `tests.md` 添加测试用例

### 15.3 文件修改建议

| 目标 | 文件 |
|------|------|
| 修改线程行为 | `src/composables/useDesktopState.ts` |
| 修改消息渲染 | `src/components/content/ThreadConversation.vue` |
| 修改输入框 | `src/components/content/ThreadComposer.vue` |
| 修改侧边栏 | `src/components/sidebar/SidebarThreadTree.vue` |
| 修改 API 调用 | `src/api/codexGateway.ts` |
| 修改桥接逻辑 | `src/server/codexAppServerBridge.ts` |
| 修改主题 | `src/style.css` |
| 修改 CLI | `src/cli/index.ts` |

---

## 16. 项目特点与亮点

1. **极致的跨平台支持**: Linux、Windows、macOS、Android (Termux)、iOS (Tailscale)
2. **零配置启动**: `npx codexapp` 一键运行
3. **PWA 支持**: 可安装为桌面/移动应用
4. **多提供商**: 支持 OpenAI、OpenRouter、OpenCode Zen、自定义端点
5. **实时协作**: WebSocket + SSE 双通道实时更新
6. **完整终端**: 每线程一个 xterm.js 终端
7. **Git 集成**: 内置 diff 查看、暂存、撤销
8. **语音输入**: 内置语音识别
9. **Skills 生态**: 支持 Composio、MCP、GitHub Skills
10. **Telegram 桥接**: 可通过 Telegram 与 Codex 交互
11. **本地文件编辑**: 浏览器内编辑本地文件
12. **多账户**: 支持多账户切换
13. **自动 Tunnel**: 内置 Cloudflare Tunnel，外网访问

---

*文档结束*
