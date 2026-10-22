# Use Case Software-Only Scene Skill

**v0.5.0 — 用例驱动的软件内场景可视化**。本工具生成的是应用/游戏自身的内容画面，而不是软件用户或现实设备的照片。

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

工具不会自行补造 UI：信息缺失时标记 `extraction.ready=false` 并拒绝规划。`extract --ai` 可使用显式配置的模型来辅助从自由文本抽取，但必须逐条验证来源。

## 六项目官方资料驱动基准（离线）

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

## 用真实应用/游戏截图作为视觉锚点

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

## 验收

```bash
python -m unittest discover -s tests -v
```

GitHub Actions 在 Python 3.10 和 3.12 下验证本地安装、结构校验、六项目基准和离线图像合成。CI 不调用付费生图 API。真实视觉验收需检查是否有**任何**现实用户、显示器、办公桌或其他软件外物体；只要有，直接判不通过。

详细基准定义参见 [`benchmarks/famous-projects/README.md`](benchmarks/famous-projects/README.md)，人工作业对比参见 [`docs/benchmark-methodology.md`](docs/benchmark-methodology.md)。许可证 MIT。
