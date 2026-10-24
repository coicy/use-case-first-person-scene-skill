# Use-Case Driven Software Concept Designer

> **当前正式产品定义：为尚未开发或仍在设计的新软件/游戏，根据提示词和用例生成原创的软件内部场景概念图。** AI 可以主动设计 UI、交互和场景，但必须区分用户需求与 AI 提案，并保持跨用例一致性。已确认的产品规则见 [PRODUCT_REQUIREMENTS.md](docs/PRODUCT_REQUIREMENTS.md)，下一步计划见 [V07_WORK_PLAN.md](docs/V07_WORK_PLAN.md)。
>
> **实施状态：** WP-01 至 WP-04 已实现原创新产品设计和生成编排；WP-05 真实视觉验收仍未完成。Agent 自带生图为首选。以下保留 v0.6 命令文档作为兼容说明，不应将复刻既有软件当成后续默认目标。

## 生成方式优先级：Agent 自带生图（PRODUCT-003）

**本仓库是 Agent Skill。** 宿主 Agent 有图像生成工具时，优先直接调用该工具生成原创软件/游戏用例图；默认**无需 OPENAI_API_KEY**。Python CLI 只负责导出单场景任务和导入实际图片，无法直接调用任意 Agent 的私有生图工具。

```bash
ucscene design-plan benchmarks/new-products/new-asset-studio.wp02.brief.json --variants 2 --out out/plan.json
ucscene concept-packet out/plan.json --mode draft --variant VAR-01 --step STEP-001 --out out/packet.json
ucscene concept-agent-export out/packet.json --out-dir out/tasks
# Agent 自己调用生图工具：仅使用 tasks/ 内一个步骤的 TXT，保存真实 PNG
# 创建包含 variant_id、scene_id、file 和 tool 的 out/results.json
ucscene concept-agent-import out/packet.json --handoff out/tasks/manifest.json --mapping out/results.json --images out/images --out-dir out/received
ucscene concept-agent-verify out/packet.json --handoff out/tasks/manifest.json --import-manifest out/received/manifest.json
ucscene concept-gallery out/packet.json --images out/received/images --selection out/received/gallery-selection.json --out-dir out/gallery
```

独立 concept-render --execute 是**用户明确选择并授权费用**时才使用的备用 API 路径。导出任务不等于生图；导入哈希不等于验证实际提示词或图片质量；最终用例视觉验收和设计批准仍需单独进行。详细说明：[正式决策](docs/decision-003-agent-native-generation.md) · [操作指南](docs/AGENT_NATIVE_IMAGE_WORKFLOW.md)。

## v0.6 已实现功能与兼容说明

**v0.6.0 — 用例驱动的软件内场景可视化与实际图片验收**。本工具生成的是应用/游戏自身的内容画面，而不是软件用户或现实设备的照片。

## 核心定义（已修正）

- VS Code / Godot / Blender / GIMP：画面仅包含软件编辑器/窗口的 UI、视口与功能状态。
- OpenTTD：画面仅包含游戏的等距地图、工具栏和操作状态，不是玩家看着显示器的照片。
- Luanti：画面仅包含游戏内部的第一人称视角。可出现游戏本身绘制的角色手臂（如果有依据），不出现真实玩家。
- **统一禁止**：显示器边框、手机机身、键盘、桌面、办公室、现实用户、拍摄场景、分镜海报或营销展示样机。

此前“physical-user”（现实用户视角）定义是错误的，已废弃。旧版场景规划、视觉基准哈希和带现实设备的验收图片均不再有效。参见 [`docs/decision-001-software-only.md`](docs/decision-001-software-only.md)。

## 安装

```bash
python -m pip install -e .
python -m pip install -e '.[ui]'  # 可选：Pillow，用于图片校验和 UI 合成
```

Python >=3.10；核心命令无第三方运行时依赖。只有明确触发在线生成/AI 提取/视觉审查时，才需要自行设置 `OPENAI_API_KEY` 并可能产生 API 费用。

## 输入模型

- `id`, `title`, `actor`, `goal`, `environment`, `steps` 必需；environment 指软件内工作区、文档/关卡或游戏内场景。
- `frame_scope`: 固定 `software-only`。
- `viewpoint_mode`: `application-ui`（默认）或 `gameplay`。
- `game_camera`: 仅 `gameplay` 可显式指定 `first-person`, `isometric`, `top-down`, `side-scrolling`, `third-person`, `documented`。
- `device`：兼容旧输入的**可选来源元数据**，绝不出现在生图 prompt 中，也不应被渲染。
- 每个步骤定义动作、分支、状态及可以在软件内部看见的 `visible_evidence`。

## 离线体验：软件内部的出库管理页面

```bash
ucscene extract examples/warehouse-scan.md --out out/use-case.json
ucscene validate out/use-case.json
ucscene plan out/use-case.json --out out/scene-plan.json
ucscene review out/scene-plan.json
```

在 **v0.6 旧版 CLI** 中，信息缺失时可能标记 `extraction.ready=false` 并拒绝规划；这是即将改造的旧行为，不是新产品概念设计规则。**v0.7 应允许 AI 对尚未规定的 UI 细节提出可追溯的设计提案**，仅对硬性要求缺失/冲突作明确说明。`extract --ai` 在旧版中仍需要核验来源。

## v0.6 历史兼容基准：六款已有软件（离线）

```bash
ucscene benchmark benchmarks/famous-projects/suite.json \
  --lock benchmarks/famous-projects/prompt-lock.json \
  --out out/benchmark.json
ucscene benchmark-export benchmarks/famous-projects/suite.json \
  --out-dir out/benchmark-plans
ucscene benchmark-rating-template benchmarks/famous-projects/suite.json \
  --out out/ratings.json
```

共六项目、十八步骤、三十六条证据。结构通过**不等于**真实生成视觉合格。Golden lock 记录审核后的新一代软件内场景 prompt SHA-256；不能使用旧的现实设备视角基准。

## v0.6 兼容：用截图作为视觉锚点（新产品可选）

```bash
ucscene anchor-create out/scene-plan.json \
  --image assets/app-viewport.png --out assets/anchor.json \
  --approved --note '确认图片完全位于软件内部且符合项目原始 UI'
ucscene anchor-verify assets/anchor.json --plan out/scene-plan.json --require-approved

# 明确由操作者授权后，才执行付费生图
ucscene generate out/scene-plan.json --anchor assets/anchor.json --out out/generated
ucscene review-image out/scene-plan.json --step 03-fail \
  --image out/generated/UC-WH-001--03-fail.png \
  --out out/visual-review.json
```

也可通过 `generate --chain` 按顺序编辑前一张图片（有漂移风险），或 `generate --reference-image` 指定单张未备案图片。参考图必须是软件/游戏本身的内容，不接受显示器照片。

## UI 合成能力（完全离线）

`compose-ui` 和 `compose-batch` 可将用户提供的真实 UI 截图投影到**软件界面内部**的编辑区、模拟器面板、游戏内虚拟屏幕等区域。它们属于图像几何工具，用户必须提供四角点（左上、右上、右下、左下），**不再用于将 UI 嵌入现实设备照片**。多数直接软件截图无需合成，应优先直接使用原 UI 图片。

```bash
python examples/make_demo_assets.py
ucscene compose-ui \
  --scene out/demo/scene.png --ui out/demo/ui.png \
  --quad examples/screen-quad.demo.json --out out/demo/composited.png
```

该合成能力只保证几何处理与输入哈希可追溯，不保证截图真实运行、生成图内容准确、字体绝对清晰或 UI 可交互。


## 实际生成图验收画廊（v0.6）

不能只用 `benchmark` 的结构通过来宣称生图成功。本版加入 `acceptance-gallery`：将**真实图片文件**与指定基准步骤绑定，生成可离线逐张审阅的 HTML、包含 SHA-256 的 manifest，以及交互式意见导出。

准备 `selection.json`（这是示例；图片需由操作者实际提供）：

```json
{
  "samples": [{
    "scene_id": "BENCH-GODOT-MOB--03-gravity",
    "image": "godot-gravity.png",
    "origin": "conversation-image-generation",
    "notes": "图片是模型生成的概念图，不是 Godot 的实际运行截图"
  }]
}
```

```bash
ucscene acceptance-gallery benchmarks/famous-projects/suite.json \
  --selection selection.json --images images \
  --out-dir out/acceptance
ucscene acceptance-verify out/acceptance/manifest.json
# 用浏览器打开 out/acceptance/index.html，逐图检查和导出 user-visual-review.json
```

`origin` 必须明确：`conversation-image-generation`、`external-image-model`、`ucscene-cli`、`app-runtime-screenshot` 或 `manually-composited`。若声称由本 CLI 生成，必须提供与当前用例匹配的 `generation_prompt_sha256`；对外部生图工具，不会假设使用了当前基准提示词。图片文件校验和提示词校验**不代表语义审核通过**，用户确认仍须单独收集。详见 `docs/acceptance-2026-10-22.md`。

## 多步操作保持既有功能状态（v0.6）

对于软件操作，用例的后续步骤经常必须保持已创建的对象和节点关系。可以在步骤上提供经过来源核实的 `carry_forward` 字符串列表，这些事实会传入后续每一步，即使只规划最后一步也不会丢失。Godot 基准包含 `RigidBody2D` 根节点和三个子节点的延续约束，防止后续生成图擅自替换为 `CharacterBody2D`。不能将 `carry_forward` 用于凭空补充未定义的软件功能。

## 验收

```bash
python -m unittest discover -s tests -v
```

GitHub Actions 在 Python 3.10 和 3.12 下验证本地安装、结构校验、六项目基准和离线图像合成。CI 不调用付费生图 API。真实视觉验收需检查是否有**任何**现实用户、显示器、办公桌或其他软件外物体；只要有，直接判不通过。

详细基准定义参见 [`benchmarks/famous-projects/README.md`](benchmarks/famous-projects/README.md)，人工作业对比参见 [`docs/benchmark-methodology.md`](docs/benchmark-methodology.md)。许可证 MIT。

## v0.7 WP-01 — 新产品建模基础已实现（不是完整 v0.7）

WP-01 提供三个独立模型 `ProductBrief`、`DesignDecision`、`UseCaseScene`，以及组合校验 `DesignBundle`；允许从**一句原创产品构想 + 一个用例**开始，不要求已有软件或截图。AI/用户新设计方案默认 `proposed`，不会自动批准或冻结；原有 v0.6 用例迁移后标记 `review-required`。

```bash
ucscene brief-init --product-id new-studio --name "New Studio" --category desktop \
  --prompt "设计一款原创素材管理软件" --use-case "用户筛选素材并查看详情" \
  --out out/new-studio.brief.json
ucscene design-validate out/new-studio.brief.json --kind brief
ucscene design-scaffold out/new-studio.brief.json --out out/new-studio.bundle.json
ucscene design-validate out/new-studio.bundle.json --kind bundle

ucscene migrate-legacy examples/warehouse-scan.json --product-id warehouse-concept \
  --name "Warehouse Concept" --category web --out out/legacy.brief.json
```

完整模型、原创新产品示例、离线校验范围和限制参见 [WP-01 实施说明](docs/WP01_IMPLEMENTATION.md)。**WP-02 的自动 UI 设计与正式图像提示词编译仍未实现**；`design-scaffold` 输出的是未定型结构，不应直接交给旧 `generate`。


## v0.7 WP-02: new-product interface and scene design proposals (implemented)

The main product objective remains generating original **software-internal concept visuals for NEW products**, not reproducing existing application screenshots. WP-02 can now propose layouts, interactions, and per-step image prompts:

```bash
# Offline deterministic two-candidate design (does not call an AI service)
ucscene design-plan benchmarks/new-products/new-asset-studio.wp02.brief.json --variants 2 --out out/asset-design-plan.json
ucscene design-plan-review out/asset-design-plan.json
ucscene design-export out/asset-design-plan.json --variant VAR-01 --out out/asset-prompts.json

# Three game design candidates, each covering three steps
ucscene design-plan benchmarks/new-products/new-hamlet-builder.wp02.brief.json --variants 3 --out out/hamlet-design-plan.json

# Opt-in model-assisted proposals (needs OPENAI_API_KEY, may incur charges)
ucscene design-plan benchmarks/new-products/new-asset-studio.wp02.brief.json --ai --model gpt-4.1-mini --out out/ai-design-plan.json
```

Plans classify requirements as MUST/MAY/UNKNOWN, attach 2–3 candidate approaches, propose per-step controls and feedback, and compile prompts with SHA-256 hashes. The default is a **rule-based baseline**, not AI creativity; `--ai` uses the Responses API explicitly. All proposal decisions stay unapproved and unlocked. No new-product PNG is generated in WP-02; WP-03 will govern design acceptance/freeze and WP-04 image generation. See [implementation and limitations](docs/WP02_IMPLEMENTATION.md).


## v0.7 WP-03 — 产品设计规范与跨用例继承（已实现）

从 WP-02 的 2～3 个候选中，**只有得到真实用户明确确认**之后，才可建立批准版 DesignSystem；命令行的 `--approve --evidence-ref` 是调用方对该批准的自我声明，CLI 无法独立核实身份或聊天记录。

```bash
ucscene design-plan benchmarks/new-products/new-asset-studio.wp02.brief.json --variants 2 --out out/design-plan.json
# 用户明确批准 VAR-02 后：
ucscene design-system-create out/design-plan.json --variant VAR-02 --approve --evidence-ref USER-CONFIRMATION-REF --lock --out out/design-system.json
ucscene design-system-review out/design-system.json --plan out/design-plan.json
ucscene design-apply out/design-system.json benchmarks/new-products/new-asset-studio.wp02.brief.json --out out/consistent-plan.json
ucscene design-apply-review out/consistent-plan.json --system out/design-system.json --brief benchmarks/new-products/new-asset-studio.wp02.brief.json
```

冻结规范只能通过显式授权标记 `--override-lock` 加新 `--evidence-ref` 重新批准后修订。用 `design-system-diff` 识别需要重新验收的设计变化。新增 Schema：`schemas/design-system.schema.json` 和 `schemas/consistent-scene-plan.schema.json`。详细说明见 [WP-03 实施记录](docs/WP03_IMPLEMENTATION.md)。

**重要：WP-03 只输出带批准设计基线的多步骤生图提示词，不自动生图，不代表任何候选已经获得本用户真实批准。** 下一阶段 WP-04 才实现真实原创软件图片与视觉验收。


## v0.7 WP-04 — original-software concept generation (implemented)
New-product DesignPlan or ConsistentScenePlan inputs. By default, concept-render only prepares manifests; no paid calls occur.
```bash
ucscene concept-packet out/new-product-design-plan.json --mode draft --variant VAR-01 --out out/concept-packet.json
ucscene concept-render out/concept-packet.json --out out/concept-images
# Explicit paid mode requires an API key:
# ucscene concept-render out/concept-packet.json --execute --max-images 3 --out out/concept-images
ucscene concept-gallery out/concept-packet.json --images out/concept-images --report out/concept-images/generation-report.json --out-dir out/concept-gallery
ucscene concept-verify out/concept-gallery/manifest.json
```
Other packet modes: explore, consistent (approved design system and brief), revise (selected variant and explicit change request).
Each provider request has a one-use-case-step full-bleed image contract, but prompts cannot guarantee model compliance.
Real visual quality, source semantics, and single-frame composition require direct human image review.
See docs/WP04_IMPLEMENTATION.md and docs/WP04_STATUS.md.


### Optional image-composition review
Use `ucscene concept-audit PACKET --image IMAGE.png --variant VAR-01 --scene SCENE-ID --out out/visual-audit.json` to opt in to a potentially paid visual QA call. It checks whether the actual image is a single full-bleed application/game state or a montage of independent screenshots, plus in-software boundary and step evidence. The result is **advisory** and is not human approval. Calls require `OPENAI_API_KEY`.



## WP-04: 单场景失败后的定向重试

新增 `concept-observe`（离线记录明确观察，非视觉模型、非用户批准）、`concept-retry`（来源哈希与设计约束绑定的离线修复包）及 `concept-retry-verify`（重试谱系验证）。继续使用 `concept-render` 的显式 `--execute --max-images 1` 才可能触发付费生图。每条可验证链最多两次修复；不保证视觉模型遵守单帧规则。详见 [WP04_RETRY_IMPLEMENTATION.md](docs/WP04_RETRY_IMPLEMENTATION.md)。

## v0.7 Issue #3 — 目标产品身份与错误产品重试

新版本概念渲染请求（`concept-render-packet` 1.1）会把 `product_id`、`variant_id`、`scene_id`、`step_id` 绑定到**实际发给图片 API 的单场景提示词**；旧 1.0 请求包只能校验与归档，付费生成前须使用 `concept-packet` 重新构建。单帧软件画面**不等于**目标产品正确，`concept-audit` 独立审核 `target_product_match`；`concept-observe --product-match fail` 可记录人工观察到的串场并通过 `concept-retry` 生成 `wrong-product` 定向重试包（无自动付费调用）。详见 [Issue #3 修复与真实失败样本复测](docs/ISSUE03_PRODUCT_MATCH.md)。模型是否真的遵守新提示词仍需真人验收和实际 API 测试。


## WP-05 live API validation (manual, not yet passed)

The two-original-product live Images API probe is documented in [WP05 acceptance checkpoint](docs/WP05_LIVE_API_ACCEPTANCE.md). The manual-only Actions workflow `wp05-manual-api-probe.yml` requires repository `OPENAI_API_KEY` secret and explicit `YES` confirmation. It never triggers paid calls on normal push/PR. The 2026-10-24 local attempt was blocked by absent credentials; no real API PNGs or model audit results exist from that run.


## Agent-native image-routing preflight (WP-05)

Before submitting native host-image jobs, verify the Agent tool can receive an explicit prompt and isolate the current step:

```sh
ucscene concept-agent-preflight out/packet.json --capabilities out/host-capabilities.json --out out/preflight.json
```

A declared capability failure returns exit 4 with `host-native-blocked` and does **not** call a billed API. This prevents treating a context-driven montage generator as a reliably prompt-bound scene renderer. The declaration is not proof of submitted prompt or visual quality. See [WP05_AGENT_NATIVE_PREFLIGHT.md](docs/WP05_AGENT_NATIVE_PREFLIGHT.md).
