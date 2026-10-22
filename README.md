# Use Case First-Person Scene Skill

**用例驱动的第一视角场景规划与生图工具**。将软件或游戏用例的关键步骤转成具有可追溯视觉证据的第一视角场景，并在显式配置图像 API 凭据时生成 PNG。

## 当前能力（v0.1.0）

- 结构化 JSON 用例校验、正常与异常流程、场景锚点、稳定提示词 SHA-256。
- 单步或多步场景规划、第一视角构图约束、静态计划校验。
- 可选 OpenAI Images API 图片生成；未配置 API key 时不发出付费请求。
- 纯 Python 标准库 CLI 与离线单元测试，GitHub Actions 自动运行。

## 安装

需要 Python 3.10+：

```bash
python -m pip install -e .
```

## 不消耗 API 额度的快速体验

```bash
ucscene validate examples/warehouse-scan.json
ucscene plan examples/warehouse-scan.json --out out/warehouse-plan.json
ucscene review out/warehouse-plan.json
ucscene plan examples/warehouse-scan.json --step 03-fail --out out/error-only.json
```

生成的 `scene-plan.json` 含有每一步的 `prompt`、`evidence`、`step_id` 和 `prompt_sha256`。

## 可选生成真实图片

需要自行提供 API key，生成过程可能产生费用：

```bash
export OPENAI_API_KEY='your-key'
ucscene generate out/warehouse-plan.json --out out/images --model gpt-image-1.5
```

Windows PowerShell 可通过 `$env:OPENAI_API_KEY='your-key'` 设置密钥。可指定 `--step 02-scan`。

## 设计约束

- 镜头必须是当前 Actor 的真实眼睛视角，而非看着用户操作的第三人称照片。
- 每个场景必须包含与用例步骤对应的明确可视证据。
- 多场景共享环境、设备与构图锚点；图像模型的视觉一致性仍需人工检查。
- 不允许将推断的 UI、权限、状态或功能伪装为已确认需求。
- 静态 `review` 检查计划结构，不等价于实际画面审核。
- 本工具没有承诺自动理解任何自然语言文档：Agent 负责将文本转换成结构化输入。

## 目录

- `SKILL.md` — Codex/Agent 用例理解与场景生成流程
- `AGENTS.md` — 工程修改、测试和质量约定
- `src/ucscene/` — 无外部运行时依赖的 CLI、建模和可选图像提供者
- `schemas/` — 输入 Schema
- `examples/` — 包含异常分支的仓储扫描用例
- `tests/` — 无付费调用的离线单元测试
- `docs/roadmap.md` — 后续迭代方向

## 限制与安全

API 密钥仅从环境变量读取，不会写入源代码或输出。实际图片可能包含错误的 UI 文案、物理姿态或视角，必须进行人工视觉检查；CI 不会调用付费生图 API。

许可证：MIT。
