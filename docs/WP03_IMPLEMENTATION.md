# WP-03 实施记录 — 产品级 DesignSystem 与跨用例一致性

- 产品权威：[PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md)（PRODUCT-002）
- 状态：**实现且完成离线测试**。WP-04 真实 PNG 生图与用户视觉验收尚未完成。
- API 事实：本阶段使用 **self-attested** 用户批准元数据，CLI 无法独立核实聊天中是否存在该批准；开发者/Agent 不得冒用批准参数代替用户授权。

## 新能力

1. **DesignSystem**：从 `DesignPlan` 中指定 `VAR-01` / `VAR-02` / `VAR-03`，保留 layout、navigation、visual_style、controls、information_priority 和 feedback；绑定候选来源、Brief 哈希、3 项批准决策及真实批准记录引用。
2. **批准与冻结**：只有调用方明确指定 `design-system-create --approve --evidence-ref <user-message-ref>` 才创建批准状态。`--lock` 冻结布局、导航和风格。系统不会自动选中候选，也不会自行设为已批准。
3. **受控变更**：`design-system-revise` 一次改变一个产品级 UI 设计键。冻结设计仅能在 `--override-lock` 且附有新 `--evidence-ref` 时修订。修订增加版本号、历史记录、上一个版本哈希，并持续保持冻结状态。不能修改硬约束。
4. **跨用例继承**：`design-apply` 可以接受同一产品新增步骤的 ProductBrief，并生成 `ConsistentScenePlan`；不会要求新 Brief 与原始 Brief 的哈希完全相同，但会保护以前已确认的硬约束。
5. **变更影响报告**：`design-system-diff` 检查相邻版本关系与实际变更键，输出哪些设计项改变、是否要求重新审核场景。
6. **强校验**：`design-system-review` 检查来源、3 项已批准决策、硬约束、哈希与修订历史；`design-apply-review` 从源 Brief 和 DesignSystem 重构整个场景计划并验证，不能只改 prompt hash 绕过校验。

## 可运行 CLI 工作流

```bash
python -m pip install -e '.[ui,dev]'
ucscene design-plan benchmarks/new-products/new-asset-studio.wp02.brief.json --variants 2 --out out/asset-design-plan.json

# 仅用户确实明确批准某个候选后才执行。此处是命令形态示例，不表示当前用户已批准 VAR-02：
ucscene design-system-create out/asset-design-plan.json \
  --variant VAR-02 --approve --evidence-ref USER-CONFIRMATION-REFERENCE --lock \
  --out out/asset-design-system.json
ucscene design-system-review out/asset-design-system.json --plan out/asset-design-plan.json

# 对同一产品已有/新增用例进行场景设计继承（不产生 PNG 图片）：
ucscene design-apply out/asset-design-system.json \
  benchmarks/new-products/new-asset-studio.wp02.brief.json \
  --out out/asset-consistent-plan.json
ucscene design-apply-review out/asset-consistent-plan.json \
  --system out/asset-design-system.json \
  --brief benchmarks/new-products/new-asset-studio.wp02.brief.json

# 冻结规范修订时必须有用户最新授权；工具本身无法认证 evidence-ref 所指向的信息：
ucscene design-system-revise out/asset-design-system.json --key ui.layout \
  --value 'A user-approved alternative layout' --approve \
  --evidence-ref USER-SECOND-CONFIRMATION --override-lock \
  --out out/asset-revised.json
ucscene design-system-diff out/asset-design-system.json out/asset-revised.json \
  --out out/asset-design-diff.json
```

## 工程合同与缺口

- `DesignSystem` 是已批准的设计规范记录，不是用户授权的加密签名。哈希用于完整性检测，不能证明是谁批准。
- 已冻结的三个产品键：`ui.layout`、`ui.navigation`、`ui.visual_style`。`controls`、`information_priority`、`feedback` 也固化为基线并用于后续场景，但本阶段的 `revise` 命令仅允许修改前述三个键；其他元素需要未来的细粒度设计变更合同。
- 约束冲突校验针对机器可识别的结构化键；无法充分证明任意自然语言需求的逻辑一致性。
- 新用例规划输出完整提示词、必需证据、UI 文本和 SHA-256；此阶段**没有实际生图、没有视觉准确率，也没有对用户的产品设计方案作过批准**。
- WP-02 的旧 `DesignPlan` 仍保持原样；WP-03 在独立 `DesignSystem` 中管理已批准的设计，不反向篡改原始候选和批准状态。
- 未选择新候选时，工具不会从 2～3 个候选中自行选“最佳方案”；这是保留的用户设计裁决权限。
- 新软件 UI 所在软件画面仍受 PRODUCT-001（software-only）约束，不允许出现实际用户和物理设备。

## 验收范围

- `tests/test_design_system.py`：显式选择、冻结修改保护、字段冲突、决策/图像提示词哈希、旧 Brief 与新 Brief 应用、游戏内画面边界、版本差异和 CLI 端到端。
- GitHub Actions：Python 3.10 与 3.12、全部单元测试、两类原创产品的候选→测试批准→连续场景计划烟测、旧命令兼容。
- 测试批准凭证标记为 `CI-SYNTHETIC-*`；只表示代码路径被测试，**不是实际用户批准**。

下一阶段 WP-04 应提供真实付费 API 生图、设计候选对比、准确 UI 文本叠加和视觉审核，才可申明有完整可交付图片。
