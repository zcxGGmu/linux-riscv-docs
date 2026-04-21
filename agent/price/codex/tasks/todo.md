# TODO

## Plan

- [x] 检查当前目录结构，确认是否已有任务与经验文件
- [x] 创建任务跟踪文件并记录本次执行计划
- [x] 调研 `GLM-5.1`、`Claude Opus 4.6`、`GPT-5.4` 的最新公开定价与使用限制，优先官方来源
- [x] 建立 20 人团队月度 token 用量评估模型，覆盖需求生成、代码开发、测试验证三类环节
- [x] 生成中文 Markdown 汇报文档，包含来源、日期、口径、估算公式与结论
- [x] 自检文档的日期、单位、价格口径和计算过程

## Notes

- 当前目录为空，需要直接创建交付文档与任务文件。
- 本次研究优先采用官方文档/定价页；若官方未明确披露某项限制，则注明“未公开”。

## Review

- 已输出 `2026-04-15-llm-pricing-and-usage-report.md`。
- 价格部分优先引用官方定价页/模型页；`GLM-5.1` 单价来自智谱官方价格页前端静态资源提取。
- 用量部分采用显式假设建模，并给出保守/基线/激进三档，避免伪精确。

## PPT Task

- [x] 复用现有调研文档，提炼适合 PPT 的核心结论与数据表
- [x] 明确 PPT 目标受众与汇报风格
- [x] 设计 PPT 结构与页数分配
- [x] 生成可交付 PPT 文件
- [x] 验证 PPT 文件可打开且主要页面内容完整

## PPT Review

- 已生成 `2026-04-15-llm-pricing-and-usage-report.pptx`。
- 已补充生成脚本 `ppt/generate_llm_pricing_report.py` 与自动校验 `tests/test_generate_llm_pricing_report.py`。
- 验证结果：
  - `python -m pytest tests/test_generate_llm_pricing_report.py -v` 通过，`3 passed`
  - `python-pptx` 可成功打开 PPT，页数为 `12`
  - `libreoffice --headless --convert-to pdf` 可成功将 PPT 转为 PDF
