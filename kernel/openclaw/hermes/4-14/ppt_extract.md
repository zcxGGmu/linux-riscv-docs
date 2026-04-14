<!-- Slide number: 1 -->

AI 辅助内核开发能力对比

$ repo grep compatible
Hermes vs OpenClaw
$ make ARCH=arm64 olddefconfig
为什么“工程执行型 Agent”更适合 Linux 内核 / 驱动 / BSP 团队
$ make -j16 drivers/clk/
[  2.417] probe defer: regulator not ready
汇报对象：管理层 / 技术负责人汇报目标：
选型判断与能力定位核心结论：
Hermes 更适合作为内核研发辅助 Agent
$ git diff -- drivers/clock/foo.c
$ write RCA + next actions

执行闭环 > 触达入口
1
基于当前目录中的分析文档自动生成

### Notes:

<!-- Slide number: 2 -->
一句话结论
聚焦 AI 辅助 Linux 内核 / 驱动 / BSP 研发，而非泛化个人助手场景

OpenClaw 更擅长
Hermes 更擅长

最终判断
多渠道、长期在线的个人 AI 助手平台
Gateway / 消息入口 / 语音 / Canvas 等产品化体验
让助手在更多终端和工作区“可触达”
直接进入代码仓、本地工具链和文件系统工作
围绕查问题、改代码、跑构建、看日志形成闭环
把技能、记忆、文档沉淀成团队长期资产
在 AI 辅助 Linux 内核 / BSP 开发场景里，Hermes 更直接提升生产力。
原因不在于入口更多，而在于它更像一个能直接下场干活的工程执行型 Agent。

结论归纳：OpenClaw 解决“助手在哪用”；Hermes 解决“助手怎样真正参与研发”。
2
执行型 Agent 更匹配低层研发的真实瓶颈

### Notes:

<!-- Slide number: 3 -->
内核研发真正需要 AI 做什么？
关键不只是问答，而是进入真实研发现场，打通查-改-编-测-记的执行闭环

搜索

Patch

编译
1
2
3
查结构体、宏、Kconfig、DTS、调用链
局部改代码、设备树、文档
运行 make / 脚本 / 交叉编译

日志

分析

沉淀
4
5
6
看 warning、link error、dmesg、boot log
定位 root cause 与影响范围
写 RCA、流程、团队技能

核心判断：在 Linux 内核 / BSP 场景里，“执行”比“触达”更重要。
3
AI 价值取决于是否真正进入源码树与构建系统

### Notes:

<!-- Slide number: 4 -->
OpenClaw 与 Hermes 的设计中心不同
两者都强，但优化目标不一样：一个偏平台触达，一个偏工程执行

OpenClaw：assistant platform
Hermes：engineering agent

personal AI assistant / local-first gateway
multi-channel inbox、voice、canvas、companion apps
多代理路由、多入口接入、长期在线体验
重点回答：助手在哪些入口可用？
CLI Agent，围绕终端、文件、源码树工作
read / search / patch / write / terminal 执行闭环
delegate_task、skill、memory 支持复杂问题拆解与沉淀
重点回答：助手怎样真正参与研发？

设计中心差异
4
不是谁强谁弱，而是谁更匹配当前研发目标

### Notes:

<!-- Slide number: 5 -->
Hermes 的 4 个核心优势
在内核开发里，真正拉开差距的是源码树就地作业、构建验证闭环和复杂问题分治能力

更贴近源码树
更贴近构建系统

1
2
就地搜索、阅读、修改 C / DTS / Kconfig / 文档
可直接调用 shell、脚本、编译与验证命令

更适合复杂问题拆解
更利于长期知识沉淀

3
4
子代理并行分析 crash、probe、性能回退
技能、记忆、文档一体化保留团队经验

Hermes 不是把 AI 放在聊天入口，而是把 AI 放在工程闭环里。
5
优势来自工作形态，而不只是模型能力

### Notes:

<!-- Slide number: 6 -->
Hermes 在哪些低层场景更有价值？
这些任务共同特点是：需要同时看代码、日志、配置与文档，并持续迭代验证

驱动 probe 失败定位
DTS 与驱动不匹配分析
交叉编译/链接错误处理
查 compatible、时钟、regulator、EPROBE_DEFER
检查节点、binding、phandle、覆盖关系
定位 symbol、Kconfig、only-build-break 问题

性能回退分析
上游提交流程辅助
更多场景
并行查看 diff、热路径、锁竞争与配置变化
同步补 patch、commit message、设计说明
bring-up / suspend-resume / PM / clock / regulator

6
典型价值来自低层复杂场景，而不是泛化问答

### Notes:

<!-- Slide number: 7 -->
分维度对比：谁更适合内核研发？
对个人助手场景，OpenClaw 很强；对低层研发场景，Hermes 更关键

维度
Hermes
OpenClaw
更适合内核开发

产品中心
工程执行 Agent
多渠道助手平台
Hermes

源码树就地作业
强
非核心主叙事
Hermes

构建 / 验证闭环
强
非主卖点中心
Hermes

文件精细 patch
强
平台能力导向更强
Hermes

多渠道接入
一般
极强
OpenClaw

语音 / 移动端 / Canvas
非重点
很强
OpenClaw

判断标准不是“谁的入口更多”，而是“谁更能打穿代码-构建-日志-文档这条链”。
7
表格对比展示了两者优化目标的根本差异

### Notes:

<!-- Slide number: 8 -->
为什么这不只是工具差异，而是效率模型差异
从管理层视角，真正值得关注的是提效、降错和知识复利的可持续性

短期
中期
长期
提效
降错
沉淀知识资产
AI 直接参与仓库、构建、日志和文档，降低工程执行摩擦
跨 DTS、driver、Kconfig、日志的联动问题更容易被系统化定位
把个人经验固化为技能、记忆和可复用工作流，形成团队复利
8
管理价值 = 提效 + 降错 + 团队知识复利

### Notes:

<!-- Slide number: 9 -->
最终建议
什么时候选 OpenClaw，什么时候选 Hermes

更适合 OpenClaw 的情况
更适合 Hermes 的情况

需要多渠道助手、长期在线和丰富入口
需要 Telegram / Slack / Discord / WhatsApp 等覆盖
强调移动端、语音、Canvas 等交互体验
建设目标是 assistant platform
目标是 Linux 内核 / 驱动 / BSP 团队提效
需要 AI 深入代码分析、patch、编译、日志和文档沉淀
需要沉淀调试套路、构建命令和项目约定
建设目标是 engineering agent

一句话总结：OpenClaw 更像“把 AI 放到很多地方去用”，Hermes 更像“把 AI 放进研发现场里干活”。
9
对 AI 辅助 Linux 内核 / BSP 开发，优先考虑工程执行型 Agent

### Notes:
