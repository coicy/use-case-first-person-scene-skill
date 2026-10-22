# Use Case First-Person Scene Skill

**用例驱动第一视角场景生成技能**：从软件/游戏用例提取关键体验节点，生成可追溯的场景计划，再按需要生图、保持视觉锚点、离线融合真实 UI，并做视觉质量检查。

核心输出是**用户亲眼看到、实际正在交互的场景**，而不是 UML 关系图、第三人称人物像或伪造的应用截图。

## v0.3.0 — 已实现的命令

| 命令 | 在线 API | 做什么 |
| --- | --- | --- |
| `extract` | 否 | 解析有约定字段/步骤格式的中文英文 Markdown 用例 |
| `extract --ai` | **是** | 从自由文本中提取必须带原文引证的字段；无证据的字段保持待补充 |
| `validate` / `plan` / `review` | 否 | 校验用例、生成稳定的第一视角提示词和场景计划、做静态检查 |
| `anchor-create` / `anchor-verify` | 否 | 将参考图及用例锚点绑定到带 SHA-256 的清单；显式操作员审批 |
| `generate` | **是** | 实际生图，支持独立生成、固定参考图、逐图链式编辑以及经核验的 anchor manifest |
| `compose-ui` | 否 | 将**原始 UI 截图**透视映射到生成场景的设备屏幕区域 |
| `compose-batch` | 否 | 按用例步骤 ID 对多张场景分别合成真实 UI，预检全部输入并生成溯源清单 |
| `review-image` | **是** | 可选视觉模型审查 POV、逐项证据、UI 文案与参考图一致性 |

**边界：** `compose-ui` 是透视几何合成，不能自动定位设备屏幕；需要由设计人员指定四角。`anchor-create --approved` 记录的是操作员的声明，不是算法认证。真实 UI 截图经过透视缩放后不保证小字仍清晰，因此需人工查看导出画面。参考图图片编辑仍可能漂移。所有 API 命令都需要用户自行配置 `OPENAI_API_KEY`，且可能产生费用；正常离线命令与 CI 不调用在线服务。

## 安装

Python 3.10+：

```bash
# 仅用例、场景提示词和在线图像 API（标准库）
python -m pip install -e .

# 启用本地参考图校验与 UI 透视合成
python -m pip install -e '.[ui]'
```

在 Windows PowerShell 需要将 `'.[ui]'` 保持为完整的一段参数。

## 1. 从用例到多步骤场景计划（离线）

```bash
ucscene extract examples/warehouse-scan.md --out out/use-case.json
ucscene validate out/use-case.json
ucscene plan out/use-case.json --out out/scene-plan.json
ucscene review out/scene-plan.json
```

`extract` 支持 `用例编号/参与者/目标/环境/设备` 等字段，`## 主流程`、`## 异常流程`、`## 替代流程` 等段落。步骤格式例如 `1. 扫描商品 | 画面: 扫码枪、商品条形码`。

**信息缺失时不可自动填造：** 生成的 JSON 会带 `extraction.ready=false` 和缺失项，退出码为 3；`plan` 将拒绝未完成的草案。也可以显式用 `--actor` 等参数补充**人为确认**的信息。纯自由文本提取需要使用 `extract --ai` 并人工检查引证。

## 2. 建立经核验的场景参考图（v0.3，离线）

首先准备一张你人工认可的第一视角参考图 PNG/JPEG/WebP。它可以是项目内已有的原型、AI 图或拍摄的照片。然后运行：

```bash
# 未经人工确认时，创建的是未批准草案；不会被 generate --anchor 接受
ucscene anchor-create out/scene-plan.json \
  --image assets/warehouse-reference.png \
  --out assets/warehouse-anchor.json

# 人工确认视角、场所、设备、构图之后，使用 --approved 建立正式引用
ucscene anchor-create out/scene-plan.json \
  --image assets/warehouse-reference.png \
  --out assets/warehouse-anchor.json \
  --approved --note '人工确认货架、设备及眼睛视角'

ucscene anchor-verify assets/warehouse-anchor.json \
  --plan out/scene-plan.json --require-approved
```

Manifest 存储了图片相对路径、SHA-256、像素尺寸、用例 ID 和场景锚点指纹。**若图片被修改，或用例的场景锚点变化，将拒绝复用，避免无意的参考图漂移。** Manifest 本身不是数字签名，不防范有权限修改清单的恶意攻击者。

### 可选：使用固定锚点做真实生图（会产生 API 费用）

```bash
export OPENAI_API_KEY='your-own-key'
ucscene generate out/scene-plan.json \
  --anchor assets/warehouse-anchor.json \
  --out out/generated
```

此命令将同一已验证参考图作为每张场景编辑的输入，先对引用完整性做离线预检。与 `--reference-image` / `--chain` 互斥。*参考图一致不等于生成图一致*；输出依然需要 `review-image` 检查及人工评审。

## 3. 真实 UI 截图透视合成（v0.3，完全离线）

用户手工给出设备屏幕的四角，依次是**左上、右上、右下、左下**，坐标为相对场景图片宽高的 0～1 归一化数值。

```json
{
  "coordinate_system": "normalized",
  "points": [[0.35, 0.20], [0.68, 0.22], [0.67, 0.70], [0.34, 0.72]]
}
```

确认多边形凸且顺序正确，不应覆盖设备边框或手指。命令：

```bash
ucscene compose-ui \
  --scene out/generated/UC-WH-001--02-scan.png \
  --ui assets/real-ui-step-02.png \
  --quad assets/screen-quad-02.json \
  --out out/composited/UC-WH-001--02-scan-ui.png \
  --report out/composited/step-02-report.json
```

它把用户提供的真实屏幕截图（不是模型猜测的 UI）通过透视变换合到画面，背景和屏幕外区域不变，最终 PNG 与 JSON 记录源图/UI图/坐标文件以及结果的 SHA-256。**不执行 OCR、不保证运行时功能、不自动验证透视位置和文字清晰度。** 透视变形会使很小的文字像素模糊。

### 多步骤使用不同 UI 截图

在 `assets/ui-map.json` 中设置相对**映射文件所在目录**的路径：

```json
{
  "format_version": "1.0",
  "screens": {
    "02-scan": {"ui": "scan-active.png", "quad": "screen-quad-02.json"},
    "03-fail": {"ui": "scan-error.png", "quad": "screen-quad-03.json"}
  }
}
```

```bash
ucscene compose-batch out/scene-plan.json \
  --images out/generated \
  --map assets/ui-map.json \
  --out out/composited
```

默认仅合成映射中列出的步骤，并在 `composition-report.json` 标明未映射的步骤。使用 `--strict` 则要求场景计划中的每个步骤都配置截图。执行前预检查所有目标文件/图片和坐标，避免已合成部分图片之后才遇到缺失文件。批量命令不会调用在线 API。

## 4. 一条命令复现 UI 透视的离线演示

仓库包含**手工绘制的合成测试素材生成器**，不需要真实图片或 API Key：

```bash
python examples/make_demo_assets.py
ucscene compose-ui \
  --scene out/demo/scene.png \
  --ui out/demo/ui.png \
  --quad examples/screen-quad.demo.json \
  --out out/demo/composited.png \
  --report out/demo/composite-report.json
```

`out/demo/composited.png` 是模拟的第一视角仓库扫码设备概念草图，已在屏幕上透视合成另一张手工绘制的演示 UI。它只证明离线合成链路工作，不代表 AI 真正生成的照片或已实现的产品界面。

## 5. 对真实生成图做视觉审查（在线，可选）

```bash
ucscene review-image out/scene-plan.json \
  --step 02-scan \
  --image out/generated/UC-WH-001--02-scan.png \
  --reference-image assets/warehouse-reference.png \
  --out out/audits/step-02.json
```

输出 `pass/fail/uncertain`；不确定即不算通过，审查依然是模型辅助意见而非客观证明。对 *合成后的 UI 图* 可以把 `--image` 指向 `-ui.png` 结果，以检查视觉效果。

## Codex / Agent 集成

- [`SKILL.md`](SKILL.md)：触发条件、用例到第一视角视觉规划及生图流程。
- [`AGENTS.md`](AGENTS.md)：工程修改和验收门槛。
- [`schemas/use-case.schema.json`](schemas/use-case.schema.json)：结构化用例输入。
- [`examples/warehouse-scan.md`](examples/warehouse-scan.md)：中文异常流程示例。
- [`docs/roadmap.md`](docs/roadmap.md)：范围、限制及后续路线。

## 开发和验收

```bash
python -m unittest discover -s tests -v
```

GitHub Actions 使用 Python 3.10 / 3.12 安装 UI 扩展，运行离线测试和真实 CLI 冒烟测试。**CI 不会触发付费生图或视觉审查**。许可证：MIT。
