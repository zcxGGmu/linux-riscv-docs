const pptxgen = require('pptxgenjs');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'Hermes';
pptx.company = 'Hermes';
pptx.subject = 'Hermes vs OpenClaw technical review';
pptx.title = 'Hermes vs OpenClaw：面向 Linux 内核/BSP 团队的技术评审版';
pptx.lang = 'zh-CN';
pptx.theme = {
  headFontFace: 'Aptos Display',
  bodyFontFace: 'Aptos',
  lang: 'zh-CN'
};

const C = {
  navy: '122033',
  blue: '1B5FA7',
  teal: '0E9F9A',
  light: 'F4F7FB',
  white: 'FFFFFF',
  text: '1C2430',
  muted: '5B6575',
  line: 'D7E1EA',
  green: '21845C',
  purple: '6A5AE0',
  gold: 'F3B63F',
  softBlue: 'EEF5FD',
  softTeal: 'EEF9F8',
  softPurple: 'F3F1FE',
  softGold: 'FFF6E4',
  softGray: 'F8FAFC',
  red: 'D64545'
};

function addHeader(slide, title, subtitle) {
  slide.addText(title, {
    x: 0.6, y: 0.34, w: 8.5, h: 0.42,
    fontFace: 'Aptos Display', fontSize: 24, bold: true, color: C.navy, margin: 0
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.6, y: 0.8, w: 11.6, h: 0.26,
      fontSize: 9.5, color: C.muted, margin: 0
    });
  }
}

function addFooter(slide, txt, num, dark=false) {
  slide.addText(txt, {
    x: 0.6, y: 7.02, w: 11.0, h: 0.18,
    fontSize: 8, color: dark ? 'C9D4E3' : C.muted, margin: 0
  });
  slide.addText(String(num), {
    x: 12.15, y: 6.98, w: 0.5, h: 0.18,
    fontSize: 8, color: dark ? 'C9D4E3' : C.muted, align: 'right', margin: 0
  });
}

function pill(slide, x, y, w, text, fill, color='FFFFFF') {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h: 0.28, rectRadius: 0.07,
    fill: { color: fill }, line: { color: fill, pt: 0 }
  });
  slide.addText(text, {
    x, y: y + 0.06, w, h: 0.12,
    fontSize: 9, bold: true, color, align: 'center', margin: 0
  });
}

function sectionCard(slide, x, y, w, h, title, body, fill='FFFFFF', accent=C.blue) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: fill }, line: { color: C.line, pt: 1 }
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: x + 0.18, y: y + 0.16, w: w - 0.36, h: 0.28, rectRadius: 0.06,
    fill: { color: accent }, line: { color: accent, pt: 0 }
  });
  slide.addText(title, {
    x: x + 0.25, y: y + 0.22, w: w - 0.5, h: 0.12,
    fontSize: 11.8, bold: true, color: C.white, align: 'center', margin: 0
  });
  if (Array.isArray(body)) {
    const runs = [];
    body.forEach((b) => runs.push({ text: b, options: { bullet: { indent: 12 }, breakLine: true } }));
    slide.addText(runs, {
      x: x + 0.18, y: y + 0.56, w: w - 0.36, h: h - 0.68,
      fontSize: 9.5, color: C.text, margin: 0.035, paraSpaceAfterPt: 4, valign: 'top'
    });
  } else {
    slide.addText(body, {
      x: x + 0.2, y: y + 0.56, w: w - 0.4, h: h - 0.7,
      fontSize: 9.8, color: C.text, margin: 0.02, valign: 'top'
    });
  }
}

function metricBox(slide, x, y, w, h, k, t, body, fill, accent) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: fill }, line: { color: C.line, pt: 1 }
  });
  slide.addShape(pptx.ShapeType.ellipse, {
    x: x + 0.18, y: y + 0.18, w: 0.52, h: 0.52,
    fill: { color: accent }, line: { color: accent, pt: 0 }
  });
  slide.addText(String(k), {
    x: x + 0.34, y: y + 0.33, w: 0.18, h: 0.12,
    fontSize: 10, bold: true, color: C.white, align: 'center', margin: 0
  });
  slide.addText(t, {
    x: x + 0.86, y: y + 0.2, w: w - 1.02, h: 0.18,
    fontSize: 13.2, bold: true, color: C.navy, margin: 0
  });
  slide.addText(body, {
    x: x + 0.18, y: y + 0.82, w: w - 0.36, h: h - 0.98,
    fontSize: 9.7, color: C.text, margin: 0.02
  });
}

function cover() {
  const s = pptx.addSlide();
  s.background = { color: C.navy };
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: C.navy }, line: { color: C.navy, pt: 0 } });
  s.addShape(pptx.ShapeType.rect, { x: 8.5, y: 0, w: 4.833, h: 7.5, fill: { color: '1A3550' }, line: { color: '1A3550', pt: 0 } });
  pill(s, 0.8, 0.82, 2.3, '技术评审版', C.teal);
  s.addText('Hermes vs OpenClaw', {
    x: 0.8, y: 1.55, w: 6.5, h: 0.52,
    fontFace: 'Aptos Display', fontSize: 26, bold: true, color: C.white, margin: 0
  });
  s.addText('面向 Linux 内核 / 驱动 / BSP 团队的 AI Agent 技术评审', {
    x: 0.82, y: 2.2, w: 6.7, h: 0.34,
    fontSize: 15, color: 'D8E3F0', margin: 0
  });
  s.addText([
    { text: '评审关注点：', options: { bold: true, color: C.white } },
    { text: '源码树作业、构建验证闭环、复杂缺陷分治、知识沉淀', options: { color: 'D8E3F0' } },
    { text: '适用对象：', options: { breakLine: true, bold: true, color: C.white } },
    { text: 'Kernel / Driver / DTS / Kconfig / Bring-up / Performance', options: { color: 'D8E3F0' } },
    { text: '结论预告：', options: { breakLine: true, bold: true, color: C.white } },
    { text: 'Hermes 更像进入研发现场的 engineering agent', options: { color: '7BE0D6' } }
  ], {
    x: 0.82, y: 3.05, w: 5.9, h: 1.45, fontSize: 12, margin: 0.02, paraSpaceAfterPt: 8
  });

  const code = [
    '$ rg "compatible" arch/ drivers/ dts/',
    '$ make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-',
    'ld.lld: undefined reference to foo_clk_init',
    '[   3.821] probe defer: regulator not ready',
    '$ git diff -- drivers/clk/foo.c',
    '$ write RCA + patch plan + regression notes'
  ];
  s.addShape(pptx.ShapeType.roundRect, {
    x: 8.95, y: 1.0, w: 3.65, h: 5.1, rectRadius: 0.08,
    fill: { color: '0C1828' }, line: { color: '35516E', pt: 1.2 }
  });
  s.addShape(pptx.ShapeType.rect, {
    x: 8.95, y: 1.0, w: 3.65, h: 0.42,
    fill: { color: '223A54' }, line: { color: '223A54', pt: 0 }
  });
  ['F87171', 'F3B63F', '34D399'].forEach((col, i) => {
    s.addShape(pptx.ShapeType.ellipse, {
      x: 9.12 + i * 0.22, y: 1.12, w: 0.1, h: 0.1,
      fill: { color: col }, line: { color: col, pt: 0 }
    });
  });
  code.forEach((line, idx) => {
    s.addText(line, {
      x: 9.18, y: 1.62 + idx * 0.63, w: 3.05, h: 0.24,
      fontFace: 'Consolas', fontSize: 9.7,
      color: idx === 2 || idx === 3 ? C.gold : 'D6E3F2', margin: 0
    });
  });
  s.addShape(pptx.ShapeType.roundRect, {
    x: 8.95, y: 6.22, w: 3.65, h: 0.48, rectRadius: 0.06,
    fill: { color: C.teal }, line: { color: C.teal, pt: 0 }
  });
  s.addText('核心评判标准：执行闭环深度', {
    x: 9.2, y: 6.37, w: 3.15, h: 0.14,
    fontSize: 11.5, bold: true, color: C.white, align: 'center', margin: 0
  });
  addFooter(s, '当前目录中的技术分析文档自动汇总生成', 1, true);
}

function technicalQuestion() {
  const s = pptx.addSlide();
  s.background = { color: C.light };
  addHeader(s, '先定义评审问题：低层研发到底需要什么样的 AI Agent？', '如果评审目标是 Linux 内核 / BSP 提效，评价标准应围绕真实工程动作，而不是消息入口数量');

  sectionCard(s, 0.72, 1.45, 2.95, 2.05, '代码理解类', [
    '搜索结构体、宏、Kconfig、DTS 节点',
    '跟踪 symbol 定义与调用路径',
    '比较不同架构/SoC 的实现差异'
  ], C.white, C.blue);
  sectionCard(s, 3.93, 1.45, 2.95, 2.05, '修改与验证类', [
    '小步 patch 驱动 / DTS / Kconfig / 文档',
    '运行 make、脚本与检查工具',
    '读取 warning / error / linker 报错'
  ], C.white, C.teal);
  sectionCard(s, 7.14, 1.45, 2.95, 2.05, '调试与定位类', [
    '分析 boot log、dmesg、oops、panic',
    '追踪 probe defer / clock / regulator 依赖',
    '定位性能回退与回归引入点'
  ], C.white, C.purple);
  sectionCard(s, 10.35, 1.45, 2.25, 2.05, '长周期协作', [
    '沉淀复现步骤与调试流程',
    '保留平台约束与提交规范',
    '输出 RCA 与回归记录'
  ], C.white, C.gold);

  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.92, y: 4.1, w: 11.65, h: 1.72, rectRadius: 0.08,
    fill: { color: C.white }, line: { color: C.line, pt: 1 }
  });
  s.addText('低层研发的典型闭环', {
    x: 1.18, y: 4.32, w: 1.9, h: 0.18,
    fontSize: 15, bold: true, color: C.navy, margin: 0
  });
  const steps = ['查定义', '改代码', '跑构建', '看日志', '复盘沉淀'];
  steps.forEach((it, i) => {
    const x = 1.18 + i * 2.2;
    s.addShape(pptx.ShapeType.roundRect, {
      x, y: 4.82, w: 1.55, h: 0.42, rectRadius: 0.06,
      fill: { color: i % 2 === 0 ? C.softBlue : C.softTeal }, line: { color: C.line, pt: 1 }
    });
    s.addText(it, {
      x, y: 4.95, w: 1.55, h: 0.12,
      fontSize: 10.5, bold: true, color: C.navy, align: 'center', margin: 0
    });
    if (i < steps.length - 1) {
      s.addShape(pptx.ShapeType.chevron, {
        x: x + 1.67, y: 4.89, w: 0.32, h: 0.18,
        fill: { color: C.gold }, line: { color: C.gold, pt: 0 }
      });
    }
  });
  s.addShape(pptx.ShapeType.roundRect, {
    x: 1.08, y: 6.1, w: 11.2, h: 0.58, rectRadius: 0.08,
    fill: { color: C.navy }, line: { color: C.navy, pt: 0 }
  });
  s.addText('结论：评审重点应是“能否打穿查-改-编-测-记闭环”，而不是“能接入多少入口”。', {
    x: 1.38, y: 6.29, w: 10.6, h: 0.16,
    fontSize: 14.5, bold: true, color: C.white, align: 'center', margin: 0
  });
  addFooter(s, '技术评审的标准必须回到真实工作负载', 2);
}

function workflowMap() {
  const s = pptx.addSlide();
  s.background = { color: C.white };
  addHeader(s, '从工作界面看：Hermes 更贴近源码树与工具链', '内核/BSP 开发天然围绕仓库目录、shell、Makefile/Kconfig/DTS、日志与 patch 运转');

  sectionCard(s, 0.72, 1.42, 4.15, 4.72, 'Hermes：工作在仓库旁边', [
    '终端执行：make、clang/gcc、脚本、检查命令',
    '文件操作：read_file / search_files / patch / write_file',
    '任务编排：todo + delegate_task 适合复杂缺陷分治',
    '知识沉淀：skill + memory 绑定项目约定与调试套路',
    '输出物一体化：patch、RCA、回归记录、说明文档'
  ], C.softBlue, C.teal);

  s.addShape(pptx.ShapeType.chevron, {
    x: 5.12, y: 3.18, w: 0.72, h: 0.52,
    fill: { color: C.gold }, line: { color: C.gold, pt: 0 }
  });
  s.addText('更靠近执行环境', {
    x: 4.88, y: 3.82, w: 1.2, h: 0.14,
    fontSize: 9, bold: true, color: C.muted, align: 'center', margin: 0
  });

  sectionCard(s, 6.05, 1.42, 3.15, 4.72, 'OpenClaw：平台触达能力强', [
    'Gateway / 多渠道 inbox / voice / canvas',
    '长期在线、入口丰富、助手平台化体验',
    '多代理路由与多工作区隔离',
    '更偏“助手在哪些界面可用”'
  ], C.softPurple, C.purple);

  sectionCard(s, 9.48, 1.42, 3.05, 4.72, '对内核研发的含义', [
    '主战场仍是源码树与 shell',
    '问题通常跨 DTS / driver / Kconfig / 日志',
    '关键在于本地闭环，不在于移动端或语音',
    '因此 Hermes 的工作形态更直接匹配需求'
  ], C.softTeal, C.blue);

  addFooter(s, '评估维度：谁更贴近真实执行环境，而不是谁更像个人助手平台', 3);
}

function capabilityStack() {
  const s = pptx.addSlide();
  s.background = { color: C.light };
  addHeader(s, 'Hermes 对低层研发更有价值的能力栈', '技术评审应关注：工具粒度、执行闭环、问题拆解能力，以及是否支持长期项目记忆');

  metricBox(s, 0.78, 1.48, 3.78, 1.82, 1, '细粒度源码操作', '按路径搜索、分页带行号读取、精准 patch，适合内核仓库的小步迭代。', C.white, C.blue);
  metricBox(s, 4.77, 1.48, 3.78, 1.82, 2, '构建与日志闭环', '直接运行 make / script / checker，围绕 warning、link error、boot log 快速迭代。', C.white, C.teal);
  metricBox(s, 8.76, 1.48, 3.78, 1.82, 3, '复杂缺陷分治', '并行查看 DTS、driver、Kconfig、diff 与日志，更适合跨层定位。', C.white, C.purple);

  metricBox(s, 0.78, 3.65, 3.78, 1.82, 4, '技能沉淀', '可把 probe 排查顺序、交叉编译命令、提交流程固化为团队技能。', C.white, C.gold);
  metricBox(s, 4.77, 3.65, 3.78, 1.82, 5, '持久记忆', '持续记住项目约定、平台限制与维护者偏好，适合长周期维护。', C.white, C.green);
  metricBox(s, 8.76, 3.65, 3.78, 1.82, 6, '文档与实现一体化', '代码、RCA、回归说明与 patch plan 可在同一上下文持续生成。', C.white, C.blue);

  s.addShape(pptx.ShapeType.roundRect, {
    x: 1.18, y: 6.08, w: 11.0, h: 0.58, rectRadius: 0.08,
    fill: { color: C.teal }, line: { color: C.teal, pt: 0 }
  });
  s.addText('核心判断：Hermes 更像“驻留在代码仓里的工程代理”，而不是“部署在多入口上的个人助手”。', {
    x: 1.46, y: 6.27, w: 10.45, h: 0.16,
    fontSize: 14.2, bold: true, color: C.white, align: 'center', margin: 0
  });
  addFooter(s, '技术优势来自操作粒度与闭环能力，而不是渠道数量', 4);
}

function scenarios() {
  const s = pptx.addSlide();
  s.background = { color: C.white };
  addHeader(s, '典型 Linux 内核 / BSP 场景：Hermes 更容易落地', '下面这些问题都不是单纯问答场景，而是需要同时查看源码、配置、日志并迭代验证的工程问题');

  sectionCard(s, 0.78, 1.48, 3.78, 1.75, '驱动 probe 失败', [
    '查 compatible、match table、clock/reset/regulator',
    '结合 dmesg 与 probe 路径定位 -EPROBE_DEFER'
  ], C.softBlue, C.blue);
  sectionCard(s, 4.77, 1.48, 3.78, 1.75, '设备树与驱动不匹配', [
    '核对 DTS / dtsi / binding / phandle 关系',
    '把设备树、驱动和日志放进同一分析上下文'
  ], C.softTeal, C.teal);
  sectionCard(s, 8.76, 1.48, 3.78, 1.75, '交叉编译/链接异常', [
    '围绕 undefined symbol、Kconfig 依赖快速追踪',
    '小步 patch 后立即复验'
  ], C.softPurple, C.purple);

  sectionCard(s, 0.78, 3.62, 3.78, 1.75, '性能回退分析', [
    '把 diff、热路径、锁竞争、配置变化拆成并行子任务',
    '形成阶段化调查清单与复盘说明'
  ], C.softGold, C.gold);
  sectionCard(s, 4.77, 3.62, 3.78, 1.75, '上游提交流程辅助', [
    '补 patch 切分、commit message、设计说明与回归记录',
    '更适合沉淀 maintainer 偏好和提交流程'
  ], C.softGray, C.green);
  sectionCard(s, 8.76, 3.62, 3.78, 1.75, '更多低层场景', [
    'bring-up、suspend/resume、clock、regulator、runtime PM',
    '共性是都依赖真实执行环境'
  ], C.softBlue, C.blue);

  addFooter(s, '这些场景共同验证：执行型 agent 在低层研发中更容易变成真实产出', 5);
}

function defectDecomposition() {
  const s = pptx.addSlide();
  s.background = { color: C.light };
  addHeader(s, '复杂缺陷示例：Hermes 更适合做多维度分治', '低层 bug 经常跨 DTS、driver、Kconfig、构建与 runtime 多个层次，一个视角往往看不清问题');

  s.addShape(pptx.ShapeType.roundRect, {
    x: 4.15, y: 1.42, w: 4.85, h: 0.72, rectRadius: 0.08,
    fill: { color: C.navy }, line: { color: C.navy, pt: 0 }
  });
  s.addText('示例问题：板级启动后外设 probe 失败，且 suspend/resume 异常', {
    x: 4.38, y: 1.67, w: 4.38, h: 0.16,
    fontSize: 12.2, bold: true, color: C.white, align: 'center', margin: 0
  });

  const branches = [
    { x: 0.78, y: 2.58, title: '子任务 A', body: 'DTS / dtsi / binding\ncompatible、phandle、时钟关系', fill: C.softBlue, accent: C.blue },
    { x: 3.88, y: 2.58, title: '子任务 B', body: 'driver probe / pm_ops\n错误路径、defer 逻辑、runtime PM', fill: C.softTeal, accent: C.teal },
    { x: 6.98, y: 2.58, title: '子任务 C', body: 'Kconfig / Makefile / 构建日志\n依赖缺失、only-build-break、符号缺失', fill: C.softPurple, accent: C.purple },
    { x: 10.08, y: 2.58, title: '子任务 D', body: '最近 diff / 回归引入点\n变更切面、风险范围、最小修复', fill: C.softGold, accent: C.gold }
  ];

  branches.forEach((b) => {
    s.addShape(pptx.ShapeType.line, {
      x: 6.58, y: 2.14, w: b.x + 1.1 - 6.58, h: 0.44,
      line: { color: C.line, pt: 1.6 }
    });
    s.addShape(pptx.ShapeType.roundRect, {
      x: b.x, y: b.y, w: 2.45, h: 1.7, rectRadius: 0.08,
      fill: { color: b.fill }, line: { color: C.line, pt: 1 }
    });
    pill(s, b.x + 0.18, b.y + 0.14, 0.78, b.title, b.accent);
    s.addText(b.body, {
      x: b.x + 0.18, y: b.y + 0.62, w: 2.05, h: 0.76,
      fontSize: 8.9, color: C.text, margin: 0.02, valign: 'mid'
    });
  });

  s.addShape(pptx.ShapeType.roundRect, {
    x: 2.1, y: 4.86, w: 9.1, h: 0.72, rectRadius: 0.08,
    fill: { color: C.white }, line: { color: C.line, pt: 1 }
  });
  s.addText('关键差异：Hermes 把多代理直接服务于当前工程问题的拆解与执行。', {
    x: 2.42, y: 5.1, w: 8.45, h: 0.18,
    fontSize: 11.2, color: C.text, align: 'center', margin: 0.02
  });
  addFooter(s, '对于 crash、probe、回归、性能问题，多维度并行调查的价值很高', 6);
}

function compareTable() {
  const s = pptx.addSlide();
  s.background = { color: C.white };
  addHeader(s, '表格化技术对比：哪个更利于内核 / BSP 团队？', '这里的“优先”只针对 AI 辅助低层研发场景，不针对泛化个人助手市场');
  const rows = [
    ['设计中心', '工程执行闭环', '多渠道助手平台', 'Hermes'],
    ['源码树作业', '读/搜/改/patch 一体化', '不是主叙事中心', 'Hermes'],
    ['终端/构建', 'shell / make / script / log', '可支持，但非核心卖点', 'Hermes'],
    ['复杂问题分治', '更偏问题拆解', '更偏代理路由', 'Hermes'],
    ['经验沉淀', 'skill + memory', '可做，但平台导向更强', 'Hermes'],
    ['多入口触达', '一般', '极强', 'OpenClaw']
  ];
  const x = 0.55, y = 1.42;
  const colW = [2.05, 3.45, 3.55, 2.28];
  const headers = ['维度', 'Hermes', 'OpenClaw', '本场景更优'];
  let xx = x;
  headers.forEach((h, i) => {
    const fill = i === 1 ? C.teal : (i === 2 ? C.purple : C.navy);
    s.addShape(pptx.ShapeType.rect, {
      x: xx, y, w: colW[i], h: 0.46,
      fill: { color: fill }, line: { color: C.white, pt: 1 }
    });
    s.addText(h, {
      x: xx + 0.06, y: y + 0.14, w: colW[i] - 0.12, h: 0.14,
      fontSize: 10, bold: true, color: C.white, align: 'center', margin: 0
    });
    xx += colW[i];
  });

  rows.forEach((r, idx) => {
    let cx = x;
    const bg = idx % 2 === 0 ? C.softGray : C.white;
    r.forEach((val, i) => {
      s.addShape(pptx.ShapeType.rect, {
        x: cx, y: y + 0.46 + idx * 0.64, w: colW[i], h: 0.64,
        fill: { color: bg }, line: { color: C.line, pt: 1 }
      });
      const color = i === 3 ? (val === 'Hermes' ? C.green : C.red) : C.text;
      s.addText(val, {
        x: cx + 0.08, y: y + 0.58 + idx * 0.64, w: colW[i] - 0.16, h: 0.28,
        fontSize: 8.8, color, bold: i === 3, align: 'center', margin: 0.02, valign: 'mid'
      });
      cx += colW[i];
    });
  });

  s.addShape(pptx.ShapeType.roundRect, {
    x: 1.0, y: 5.98, w: 11.3, h: 0.5, rectRadius: 0.08,
    fill: { color: C.navy }, line: { color: C.navy, pt: 0 }
  });
  s.addText('结论：如果问题被严格限定为“AI 辅助 Linux 内核 / BSP 开发”，Hermes 的相对优势更清晰。', {
    x: 1.32, y: 6.14, w: 10.65, h: 0.14,
    fontSize: 12.6, bold: true, color: C.white, align: 'center', margin: 0
  });
  addFooter(s, '表格用于技术评审，不等于否定 OpenClaw 在平台化方向的优势', 7);
}

function boundary() {
  const s = pptx.addSlide();
  s.background = { color: C.light };
  addHeader(s, '公平边界：OpenClaw 并不弱，只是优化目标不同', '技术评审要避免“绝对优劣”的误判，应明确对比前提与适用边界');

  sectionCard(s, 0.72, 1.48, 5.55, 4.3, '什么时候 OpenClaw 更值得选', [
    '目标是建设多渠道、长期在线的 AI 助手平台',
    '需要 Telegram / Slack / Discord / WhatsApp 等统一接入',
    '强调语音、移动端、Canvas 等交互形态',
    '平台层的路由、在线化和触达能力是首要诉求'
  ], C.softPurple, C.purple);

  sectionCard(s, 7.05, 1.48, 5.55, 4.3, '什么时候 Hermes 更值得选', [
    '目标是 Linux kernel / driver / BSP 团队提效',
    '需要 AI 深入参与代码理解、patch、编译、日志分析',
    '需要把调试套路、构建命令、维护者偏好沉淀下来',
    '希望 AI 从“问答工具”升级为“工程执行工具”'
  ], C.softTeal, C.teal);

  s.addShape(pptx.ShapeType.roundRect, {
    x: 1.1, y: 5.98, w: 11.15, h: 0.5, rectRadius: 0.08,
    fill: { color: C.gold }, line: { color: C.gold, pt: 0 }
  });
  s.addText('换句话说：OpenClaw 更擅长“平台化触达”，Hermes 更擅长“工程化执行”。', {
    x: 1.38, y: 6.14, w: 10.6, h: 0.14,
    fontSize: 13.4, bold: true, color: C.navy, align: 'center', margin: 0
  });
  addFooter(s, '结论成立的前提：评审对象是低层研发，而不是泛化助手平台', 8);
}

function finalRecommendation() {
  const s = pptx.addSlide();
  s.background = { color: C.navy };
  s.addText('技术评审结论', {
    x: 0.78, y: 0.72, w: 3.0, h: 0.42,
    fontFace: 'Aptos Display', fontSize: 26, bold: true, color: C.white, margin: 0
  });
  s.addText('对 AI 辅助 Linux 内核 / BSP 开发，优先考虑工程执行型 Agent', {
    x: 0.8, y: 1.2, w: 6.2, h: 0.28,
    fontSize: 12, color: 'D8E3F0', margin: 0
  });

  sectionCard(s, 0.72, 1.9, 4.15, 3.7, 'Hermes 的关键胜出点', [
    '更贴近 shell、源码树和构建系统',
    '更适合细粒度 patch',
    '更容易形成查-改-编-测-记闭环',
    '更适合复杂低层问题分治',
    '更适合沉淀平台知识与流程'
  ], C.white, C.teal);

  sectionCard(s, 5.12, 1.9, 3.3, 3.7, 'OpenClaw 的强项', [
    '多渠道入口覆盖强',
    '长期在线体验好',
    '语音 / 移动端 / Canvas 丰富',
    '更像成熟助手平台'
  ], C.white, C.purple);

  sectionCard(s, 8.67, 1.9, 3.95, 3.7, '推荐表述', [
    '平台化个人助手：优先参考 OpenClaw',
    '内核/BSP 团队提效：优先选择 Hermes 路线',
    '决策应基于工作流匹配度'
  ], C.white, C.gold);

  s.addShape(pptx.ShapeType.roundRect, {
    x: 1.05, y: 5.98, w: 11.25, h: 0.56, rectRadius: 0.08,
    fill: { color: C.teal }, line: { color: C.teal, pt: 0 }
  });
  s.addText('一句话总结：OpenClaw 更像“把 AI 放到很多地方去用”，Hermes 更像“把 AI 放进研发现场里干活”。', {
    x: 1.35, y: 6.16, w: 10.65, h: 0.18,
    fontSize: 13.2, bold: true, color: C.white, align: 'center', margin: 0
  });
  addFooter(s, '技术评审版：结论限定在 Linux 内核 / 驱动 / BSP 场景', 9, true);
}

function auto() {
  cover();
  technicalQuestion();
  workflowMap();
  capabilityStack();
  scenarios();
  defectDecomposition();
  compareTable();
  boundary();
  finalRecommendation();
  pptx.writeFile({ fileName: 'hermes_vs_openclaw_kernel_agent_comparison_technical_review.pptx' });
}

auto();
