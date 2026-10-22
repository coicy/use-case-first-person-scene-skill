# Use Case First-Person Scene Skill

**用例驱动第一视角场景生图 Skill**，将软件及游戏用例转成可追溯的用户第一视角场景规划，并可选通过图片 API 渲染与审查。

这个项目生成的是**用户亲眼看到和正在操作的具体环境场景**，不是 UML、概念关系图、第三人称人物照，也不是已实现的应用截图。

## v0.2.0 已实现能力

| 能力 | 是否需要 API key | 描述 |
| --- | --- | --- |
| `extract` | 否 | 从带字段和步骤标题的中文/英文 Markdown 用例提取结构化草案 |
| `extract --ai` | 是 | 通过 Responses API 从自由文本中抽取有原文引用的用例草案；无法证实的字段仍会标记缺失 |
| `validate` | 否 | 校验结构化用例，阻止缺失信息的草案进入规划 |
| `plan` | 否 | 规划单个/多个第一视角场景、生成稳定 prompt 哈希及场景锚点 |
| `review` | 否 | 静态检查场景计划与 prompt，不检查真实图片 |
| `generate` | 是 | 通过 OpenAI Images API 生图，支持固定参考图和连续编辑两种模式 |
| `review-image` | 是 | 利用视觉模型核查第一视角、用例画面证据、可选参考图连续性和 UI 文字 |

项目仅使用 Python 3.10+ 标准库。使用在线功能时，OpenAI API 调用会产生费用；普通命令、安装和 CI 不会消耗付费配额。

## 安装

```bash
python -m pip install -e .
```

## 离线体验：从 Markdown 用例到场景提示词

```bash
ucscene extract examples/warehouse-scan.md --out out/warehouse.json
ucscene validate out/warehouse.json
ucscene plan out/warehouse.json --out out/warehouse-plan.json
ucscene review out/warehouse-plan.json
```

Markdown 输入支持 `用例编号/参与者/目标/环境/设备` 等字段，`## 主流程`、`## 异常流程`、`## 替代流程`，步骤采用 `1. 行为 | 画面: 可见内容一、可见内容二`。

**当信息缺失时，`extract` 会保存包含 `extraction.issues` 的草案并以退出码 3 结束。** 先补充证据，或使用 `--actor` / `--goal` / `--environment` / `--device` 显式覆盖，再进入 `plan`。工具不会自动编造缺失的用户角色和硬件。

仍可直接使用原版 JSON 示例：

```bash
ucscene validate examples/warehouse-scan.json
ucscene plan examples/warehouse-scan.json --step 03-fail --out out/error-only.json
ucscene review out/error-only.json
```

## 自由文本用例（可选 AI 提取）

```bash
export OPENAI_API_KEY="your-own-key"
ucscene extract path/to/use-case.txt --ai --model gpt-4.1-mini --out out/from-prose.json
```

响应中每个字段及画面证据必须有输入原文中的引用位置；找不到直接证据的字段必须留空，并阻止规划。模型输出仍需人工检查。`--ai` 不代表能从任何一句模糊的目标自动推断完整 UI 或环境。

## 生成真实图片（会产生 API 费用）

```bash
# 每张图片独立生成；仅通过 prompt 共享文字锚点
ucscene generate out/warehouse-plan.json --out out/images

# 所有步骤参照同一张已确认的 PNG/JPEG/WebP 图像，提升空间与设备一致性
ucscene generate out/warehouse-plan.json --reference-image assets/warehouse-anchor.png --out out/images

# 第一张重新生成，后续逐步参照上一张图片编辑（可能积累漂移）
ucscene generate out/warehouse-plan.json --chain --out out/images
```

`--reference-image` 与 `--chain` 不能同时使用；`--chain` 必须生成完整有序场景组。生成结果登记在 `out/images/generation-report.json`。参考图编辑是连贯性辅助，**不保证物体、位置、屏幕 UI 及人物手部完全一致**。API key 仅从环境读取，不保存在仓库或输出文件中。

## 图片视觉审核（可选，产生 API 费用）

```bash
ucscene review-image out/warehouse-plan.json \
  --step 02-scan \
  --image out/images/UC-WH-001--02-scan.png \
  --reference-image assets/warehouse-anchor.png \
  --out out/02-scan-audit.json
```

图片必须是 PNG、JPEG 或 WebP。审核报告核验 POV、逐条画面证据、图中文字和参考图一致性，且返回 `pass`、`fail` 或 `uncertain`；有任何不确定项便不会通过。视觉检查是**模型的参考性判断**，不是自动证明，仍需要人工复核。即便图中文字看起来正确，也不能据此证明真实软件行为正确。

## 技能接入与工程规则

- `SKILL.md`：Agent 用例抽取、第一视角取景、生成与审查的工作规范。
- `AGENTS.md`：代码、测试、安全和防需求漂移约定。
- `schemas/use-case.schema.json`：结构化字段契约。
- `examples/warehouse-scan.md`、`examples/warehouse-scan.json`：异常步骤在内的示例。
- `docs/roadmap.md`：后续的参考图资产管理、CI 集成和用例差异更新。

## 开发与验收

```bash
python -m unittest discover -s tests -v
ucscene extract examples/warehouse-scan.md --out /tmp/warehouse.json
ucscene plan /tmp/warehouse.json --out /tmp/warehouse-plan.json
ucscene review /tmp/warehouse-plan.json
```

CI 仅做离线单元测试及命令行冒烟测试，API 交互均用 Mock，不配置真实密钥、不自动生图。Apache/MIT 等依赖均未引入；许可证：MIT。
