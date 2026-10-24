# Semantic SVG scene-graph prototype / 结构化概念图实验

**状态：实验性质的架构提案，不属于已经验收的正式功能。**

目标：验证能否用结构化的业务状态、UI 元素 ID、布局坐标、交互动作和数据绑定作为图像生成的权威来源，再由同一份事实数据确定性产生多个 SVG 画面。

## 内容

- `scene-contract.json`：新游戏 Hamlet Builder 的演示用数据合同，包含对象 ID、状态转移、控件位置、绑定、用例 ID 与来源，所有数值均为演示假设。
- `scene-contract.schema.json`：示范性的 JSON Schema Draft 2020-12。还需 Python 实施运行时跨字段/跨步骤校验。
- `render.py`：使用 Python 标准库生成 SVG，验证布局、绑定及状态转移，输出 SHA-256 清单。
- `renders/step-001.svg`：选择农场；`step-002.svg`：查看产量；`step-003.svg`：分配工人完成。
- `test_contract.py`：正向和故意破坏布局/对象/数值/审批状态的 10 项测试。
- `RFC.md`：建议的正式架构与迁移路线。

## 验证

```bash
# 渲染器本身仅依赖 Python 标准库；测试中的 Schema 用例需安装 jsonschema
python -m pip install jsonschema
python -m unittest -v test_contract.py
python render.py
# 可选栅格预览
python -m pip install cairosvg
```

浏览器可以直接打开 `renders/*.svg`。每个 SVG 的 `data-scene-contract-sha256`、元素 `id` 和 `data-binding` 都可解析，三个步骤中的布局锚点相同；数值由 JSON 导出而不是让图像模型重画。此原型未包含视觉生成模型调用，不能宣称已验证 AI 艺术素材与 SVG 混合合成。

## 关键限制

原型没有声明用户批准的 UI 和数值，更不证明游戏已实现。真正产品应在基础模型里加上多设备响应布局、组件约束、动作状态机、区域图像素材以及更通用的数据绑定模型；任何设计冻结须以实际批准为依据。
