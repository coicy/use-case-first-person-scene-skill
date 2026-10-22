# 软件内部画面 · 六项目实际生图验收（2026-10-22）

## 范围

这轮样张来自同一 ChatGPT 对话中的图像生成能力，不是 `ucscene generate` 的在线 API 调用，**也不是软件本身的真实运行截图**。图片及面向用户的可离线运行画廊由独立验收包交付，GitHub 仓库保存生成画廊的可复现代码与用例。除非有可信的实际生图请求记录，不能把当前基准提示词哈希宣称为这些样张的原始 prompt。

- 六项目的单步骤样张：Godot / OpenTTD / Luanti / VS Code / Blender / GIMP。
- 图像边界：6/6 均为数字软件/游戏内部的内容，没有现实硬件、人物或桌面。该观察只覆盖本次六张样张，不代表一般成功率。
- 用例真实性：有明显待核验问题，不能整体通过。其中 Godot 修正版修正了旧图 `CharacterBody2D` 的错误；Luanti 的纹理/HUD 视觉有强烈类似 Minecraft 的倾向，不应视为忠于指定 Luanti 游戏版本；VS Code 的示例程序、调试停顿点与 Locals 的一致性仍须核对。
- Blender：选中面、挤出形变可见，但无法从一张概念图证明 E 键确实执行过。
- GIMP：裁剪框、工具状态、框外变暗均可见，无法证明所有数值和按钮精确对应产品。
- OpenTTD：等距地图、Autorail、已建轨道可见；确切 UI 图标和建造状态仍需真实软件截图对照。

## 产品设计结论

1. 用例画面边界必须是产品内容帧，而不是外部物理观察视角。
2. 跨步骤必须保留已建立的事实（Godot 的 `RigidBody2D` 根节点就是典型反例）。`carry_forward` 可声明经来源支持的阶段性状态。
3. 高精度、可读 UI、源代码、节点名与准确数据最好由实际软件截图或精确编辑图层保证，纯图像模型的 UI 不足以当作工程证据。
4. 静态计划、图像生成、哈希完整性、AI 视觉审查、独立人工验收是五个不同的环节，严禁互相替代。

## 可运行交付

`ucscene acceptance-gallery`：输入基准 suite + 已存在的图片 + 明确来源索引，输出本地 HTML、图片拷贝和 `manifest.json`。`ucscene acceptance-verify`：校验真实图片有没有缺失或被替换，但不会假装内容已正确。

### 参考资料

- Godot: https://docs.godotengine.org/en/stable/getting_started/first_2d_game/04.creating_the_enemy.html
- OpenTTD: https://wiki.openttd.org/en/Manual/Railway%20construction
- Blender: https://docs.blender.org/manual/en/4.2/modeling/meshes/editing/face/extrude_faces.html
- 其他项目参见 `benchmarks/famous-projects/suite.json`。
