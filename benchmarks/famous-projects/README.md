# 知名软件与游戏用例基准（v0.4）

本基准将**有公开官方文档的真实交互操作**转换成用户第一视角场景计划，检查规则和画面证据的结构完整性。它**不**将这些静态校验结果伪装成实际生成图片的成功率。

## 六个案例（不随项目版本变化自动更新）

| 案例 | 用例 | 视角 | 官方依据 | 节点 |
| --- | --- | --- | --- | ---: |
| Visual Studio Code | 设置断点、启动调试、观察变量 | `physical-user`（实际开发者看显示器） | https://code.visualstudio.com/docs/editor/debugging | 3 |
| Blender | 选择面、挤出、确认模型形状 | `physical-user` | https://docs.blender.org/manual/en/5.1/modeling/meshes/editing/face/extrude_faces.html | 3 |
| GIMP | 选择裁剪工具、拖拽裁剪框、应用裁剪 | `physical-user` | https://docs.gimp.org/3.0/en_GB/gimp-tutorial-quickie-crop.html | 3 |
| Godot Engine | 创建 Mob 的 RigidBody2D/子节点/重力属性 | `physical-user`（编辑器而非玩家世界） | https://docs.godotengine.org/en/stable/getting_started/first_2d_game/04.creating_the_enemy.html | 3 |
| OpenTTD | 进入铁路建设工具栏、选择车站、使用 Autorail | `physical-user`（显示器内仍是等距地图） | https://wiki.openttd.org/en/Manual/Railway%20construction | 3 |
| Luanti | 角色视角瞄准、挖掘方块、放置方块 | `avatar-eyes`（游戏角色眼睛） | https://docs.luanti.org/for-players/controls/ | 3 |

Luanti 的体素节点概念另参阅 https://docs.luanti.org/for-players/nodes/ 。这里的场景材料是**按文档手工整理的测试输入**，并非官方 PRD、官方图片、品牌授权素材或项目实际运行截图。

**实测输入与视觉设计假设的边界：** 文档依据覆盖真实操作、工具名称与部分 UI 表现；工作台外观、手部构图、天气/灯光、具体纹理、相机摆位等均是方便说明用例的视觉假设，不应被称为官方事实。第三方截图没有再分发到本仓库。

## 运行可复现结构测试（完全离线）

```sh
python -m pip install -e '.[ui]'
ucscene benchmark benchmarks/famous-projects/suite.json \
  --lock benchmarks/famous-projects/prompt-lock.json \
  --out out/benchmark-offline.json
ucscene benchmark-export benchmarks/famous-projects/suite.json \
  --out-dir out/benchmark-plans
```

`benchmark` 自动检查：每个步骤都有官方 URL 的来源 ID、用例格式通过校验、规定视角正确、计划和提示词可重复生成、prompt SHA-256 与批准的 golden lock 一致。发现来源丢失、视角不匹配、目录穿越或未经审批的提示词变更即失败。`benchmark-export` 在 **完整预检** 后导出六个可直接传给 `ucscene generate` 的 JSON 场景计划。

静态报告期望 **6 个用例、18 个步骤、36 个证据项**。`visual_evaluation.status` 固定为 `not_evaluated`，除非显式提供完整的真实图片与审查结果。这些数字只是**规划素材的覆盖度**，不是视觉模型准确率。

改变了用例或提示词代码，并且经过审查确认是预期行为后，才能更新基线：

```sh
ucscene benchmark-lock benchmarks/famous-projects/suite.json \
  --out benchmarks/famous-projects/prompt-lock.json
```

## 如何做真实生图对照实验（API 费用需自行确认）

1. 从上面的 `benchmark-export` 获取每个案例独立的场景计划。选择至少 OpenTTD 和 Luanti 两个视角相反的样例。
2. 对同一场景尝试三种条件：`prompt-only`（无参考图）、`fixed-reference`（同一张经人工审核的参考图）、`sequential-chain`（以前一张图作为编辑参考）。**同一条件控制模型、分辨率、质量、版本、顺序和允许的样本数**；图像 API 的随机性不必然受本 CLI 控制，不能直接当作可复现的模型随机种子。
3. 保存每一张源 PNG，以及 `generate` 的 `generation-report.json`。将所有案例图片汇集为 `out/benchmark-images/<case-id>--<step-id>.png`。
4. 对每张图片用 `ucscene review-image` 并将结果保存为 `out/benchmark-audits/<case-id>--<step-id>.json`。图片和审查文件必须同名对应，且哈希一致。
5. 运行：

```sh
ucscene benchmark benchmarks/famous-projects/suite.json \
  --lock benchmarks/famous-projects/prompt-lock.json \
  --images out/benchmark-images \
  --audits out/benchmark-audits \
  --out out/benchmark-visual.json
```

真实图片审查的结果 **仅是模型建议**；没有图片/审查时，报告必须显示 `not_evaluated`，仅有部分结果时显示 `incomplete`。不能因为部分图片通过就称整组模型“视觉通过”。

### 独立人工评分（建议，非已实现自动评分）

每张图由两名以上不知道条件名称的评估者独立打分，逐项 0/1/2 分：

- **POV**：镜头确实属于用户眼睛，且 OpenTTD 不被误画成司机实景、Luanti 不出现实体显示器。
- **用例可识别性**：不看 prompt 也能辨认当前操作行为。
- **来源事实符合度**：关键对象/状态符合被引用的官方文档，未擅自添加功能。
- **连续性**：同一用例三个步骤保持相机、设备、布局、风格稳定。
- **UI 可靠性**：需要精确的 UI 时，最好使用真实 UI 截图透视合成，对细小字体单独检查。

每个条件每个场景至少三次实际生成后再比较通过比例与评审者间一致性；否则样本规模不足，不应给出“某方法更好”的定量结论。

## 已执行与未执行

- **已经执行：** 六项目基准的来源引用格式/相机分类/提示词生成/固定哈希/离线 CI，包含错误输入拒绝测试。
- **没有执行：** 这六个项目的真实图像 API 批量生图、真实 UI 截图视觉核对、两名评审员盲评，以及三种生成模式的视觉统计比较。未配置支付授权时，CI 不应自动触发生图。
