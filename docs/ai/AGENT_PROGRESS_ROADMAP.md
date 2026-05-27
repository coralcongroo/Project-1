# Aputure IP Project Agent 进度与后续路线图

更新时间: 2026-05-19
适用对象: 项目管理、技术负责人、文档维护者

## 目的

这份文档从“项目治理”和“文档/知识维护”视角，汇总当前仓库内各个自定义 agent 的落地状态、已完成覆盖、剩余缺口和推荐的后续推进顺序。

说明:

- 本文关注的是 agent 在当前仓库中的治理覆盖度与可用度，不等同于对应代码功能的最终完成度。
- 结论以当前仓库中的 `.github/agents/`、`.github/instructions/`、`docs/README.md` 以及本轮已完成的文档整理结果为准。

## 当前验证状态总览

当前仓库已注册 11 个自定义 agent:

- Aputure Matter ZAP
- Aputure Commissioning Startup
- Aputure RS485 Lighting
- Aputure ESP32 Runtime
- Aputure Architecture Framework
- Aputure Build Development
- Aputure Network Ops
- Aputure Countdown Integration
- Aputure Doc Maintainer
- Aputure 151L3 Porting
- Aputure Proto UDP

当前 docs 树已完成以下治理收口:

- `docs/` 已按功能拆分为 `ai / architecture / development / features/countdown / matter / migration / network / analysis`
- 上述主要文档域均已有 path-scoped instruction 绑定
- `docs/README.md` 已成为根索引，并由根层 instruction 管理
- `docs/ai/AI_AGENT_USAGE_GUIDE.md` 已完成 agent 使用说明与任务映射

## Agent 进度矩阵

| Agent | 当前状态 | 已确认进度 | 当前主要缺口 | 推荐级别 |
|---|---|---|---|---|
| Aputure Doc Maintainer | 高 | 根索引、AI 治理、文档映射已落位；已完成首轮内容过时性审查 | 仍需扩大到更多 summary/status 文档 | P1 |
| Aputure Architecture Framework | 高 | `docs/architecture/` 已归口，结构性路径已清理；已补“历史快照/概念稿”标识 | 仍需继续细化现状与设计稿边界 | P1 |
| Aputure Build Development | 高 | `docs/development/` 已归口，旧路径已修正；已补 checklist/changelog 的历史属性说明 | 仍需继续做功能项逐条复核 | P1 |
| Aputure Network Ops | 高 | `docs/network/` 已归口，网络文档路径已校准 | 还需继续核对实际协议边界 | P1 |
| Aputure Matter ZAP | 高 | `docs/matter/` 已归口，ZAP 快照文档已更新 | 需要补完整的变更后复核流程 | P1 |
| Aputure 151L3 Porting | 高 | `docs/migration/` 已归口，迁移流程文档已建立 | 仍需持续按行为而非按文件名校正 | P1 |
| Aputure Countdown Integration | 中高 | countdown 文档域已独立且完成映射 | 需核实现文档与当前代码是否仍逐项一致 | P1 |
| Aputure ESP32 Runtime | 中高 | `docs/analysis/` 已归口到运行时/分析治理 | 仍需把“已验证结论”和“建议项”拆开 | P2 |
| Aputure Commissioning Startup | 中 | agent 已注册并可用 | 暂无独立文档域或 instruction 约束 | P2 |
| Aputure RS485 Lighting | 中 | agent 已注册并有明确职责 | 主要借道 migration/architecture，缺独立治理域 | P2 |
| Aputure Proto UDP | 中偏低 | agent 已注册并在说明中可选用 | 文档仍分散在 network 域，尚未形成单独治理面 | P3 |

## 各 Agent 当前进度与后续建议

### 1. Aputure Doc Maintainer

当前验证状态:

- 已完成 `docs/README.md` 根索引与 agent 映射矩阵收口。
- 已完成 `docs/ai/AI_AGENT_USAGE_GUIDE.md` 的治理说明与任务速查表。
- 已补齐根层 instruction，使 `docs/README.md` 不再是游离文档。
- 已完成首轮 P0 文档内容过时性审查，开始把历史快照与当前状态分层表达。

当前主要缺口:

- 首轮审查已完成，但还没有覆盖所有 summary/status/checklist 文档。

后续推荐:

1. 对全仓 docs 做一轮“内容过时性审查”，优先看 summary、checklist、status 类文档。
2. 建立“历史结论 / 当前状态 / 推荐动作”三段式文档口径，减少未来失真。

### 2. Aputure Architecture Framework

当前验证状态:

- `docs/architecture/` 已独立成域，并有对应 instruction。
- 已修正 architecture 文档中一批旧路径引用，当前已能指向 `components/framework/`、`main/app/`、`components/app/local_output/` 等真实路径。
- 已将 `PROJECT_SUMMARY.md` 明确标记为历史快照，将 `SmartLight_Architecture.md` 明确标记为概念架构文档。

当前主要缺口:

- 仍需继续梳理更多架构文档中的“概念图”“目标结构”“当前实现”边界。

后续推荐:

1. 优先审查 `PROJECT_SUMMARY.md`、`SmartLight_Architecture.md`。
2. 把“当前运行链路”和“历史/目标架构图”显式拆开，避免项目管理误读。

### 3. Aputure Build Development

当前验证状态:

- `docs/development/` 已独立成域，并有对应 instruction。
- 已修正 BUILD、DEVELOPMENT_GUIDE、QUICK_REFERENCE 里的旧组件路径和旧目录结构。
- 已将 `DEVELOPMENT_CHECKLIST.md` 明确标记为历史验证模板，并在 `CHANGELOG.md` 中补充历史路径说明。

当前主要缺口:

- 历史属性已标识，但 development 域仍需要逐条复核测试项与当前代码是否一致。

后续推荐:

1. 对 `CHANGELOG.md` 做“历史路径”标识清洗。
2. 统一 development 文档对构建入口、组件路径和配置来源的表述口径。

### 4. Aputure Network Ops

当前验证状态:

- `docs/network/` 已独立成域，并有对应 instruction。
- 已修正 network 文档中的 `mqtt_agent`、`cmd_wifi`、`common` 等旧路径。

当前主要缺口:

- 仍需确认哪些协议接口是当前主路径，哪些仅是兼容路径或草案文档。

后续推荐:

1. 审查 MQTT、UDP、AMBL、Host Protocol 文档和当前代码的一致性。
2. 在运维文档里区分“当前已启用路径”和“兼容/预留能力”。

### 5. Aputure Matter ZAP

当前验证状态:

- `docs/matter/` 已独立成域，并有对应 instruction。
- `EXTENDED_COLOR_LIGHT_ZAP_CHECKLIST.md` 已从“操作清单”转为“当前 zap 快照 + 结论”。

当前主要缺口:

- 还缺一份更明确的“改 ZAP 后如何重新验证”的固定流程沉淀。

后续推荐:

1. 把 ZAP 修改、codegen、reconfigure、构建、合规复核串成固定步骤。
2. 继续把 Matter 结论严格绑定到 `.zap` 和 CSA 文档证据。

### 6. Aputure 151L3 Porting

当前验证状态:

- `docs/migration/` 已独立成域，并有对应 instruction。
- 对应表、引脚表、迁移流程、灯光迁移计划都已进入统一目录。

当前主要缺口:

- 迁移判断仍需持续从“文件级对比”提升到“行为级对比”。

后续推荐:

1. 继续优先整理 RS485、灯控、固件升级这些最容易被误判的迁移点。
2. 遇到上游新提交时，优先更新迁移表和流程文档，而不是只改代码。

### 7. Aputure Countdown Integration

当前验证状态:

- `docs/features/countdown/` 已独立成域，并有对应 instruction。
- countdown 设计、集成、测试三类文档已经归口。

当前主要缺口:

- 文档结构完整，但还没有做一轮针对当前代码实现的逐项真实性复核。

后续推荐:

1. 核对 countdown 文档中的 API、路径、状态描述是否仍与当前实现一致。
2. 把“已完成”“待现场验证”“历史风险”三类结论拆开写。

### 8. Aputure ESP32 Runtime

当前验证状态:

- `docs/analysis/` 已纳入现有治理映射。
- 运行时分析与优化类文档已经有首选 agent 可接管。

当前主要缺口:

- 分析类文档中“实测结论”和“建议动作”仍可能混写。

后续推荐:

1. 审查 runtime/optimization 文档中的时间点、验证口径与当前代码状态。
2. 建议将“已验证问题”“已修复”“待观察”显式分栏。

### 9. Aputure Commissioning Startup

当前验证状态:

- agent 已注册，职责边界明确。
- 使用说明中已能正确引导到 commissioning、BLE、CASE、startup order 场景。

当前主要缺口:

- 目前没有独立的 commissioning 文档域，也没有专属 instruction。

后续推荐:

1. 如果 commissioning 文档会继续增长，建议单独建立文档域。
2. 在此之前，可先把 commissioning 相关现状分散记录集中到一处管理文档。

### 10. Aputure RS485 Lighting

当前验证状态:

- agent 已注册，职责边界明确。
- 当前更多通过 migration 和 architecture 文档间接承接其知识面。

当前主要缺口:

- 缺少独立的 RS485/lighting 文档治理域。

后续推荐:

1. 若 RS485/Endpoint 2/local_output 会持续演进，建议拆出独立文档域。
2. 若短期不拆域，至少补一份集中式链路总览文档，避免知识继续分散。

### 11. Aputure Proto UDP

当前验证状态:

- agent 已注册，职责边界明确。
- 使用说明中已可覆盖 `.proto`、Envelope、UDP 5568/5569 数据帧任务。

当前主要缺口:

- 文档仍主要散落在 `docs/network/`，没有独立治理面。

后续推荐:

1. 若 proto/Envelope 文档继续增多，建议从 network 域中拆出独立子域。
2. 把“当前主路径”和“旧 Message.proto 兼容路径”分开管理。

## 项目级优先级建议

从整个项目管理角度，建议按以下顺序推进:

### P0: 已完成首轮审查

- Aputure Doc Maintainer
- Aputure Architecture Framework
- Aputure Build Development

目标:

- 已完成“结构已正确但内容可能过时”的首轮审查。
- 已将项目管理、开发、架构三条主口径中的高风险历史快照文档标识清楚。

### P1: 第二批推进

- Aputure Network Ops
- Aputure Matter ZAP
- Aputure 151L3 Porting
- Aputure Countdown Integration

目标:

- 完成各专业域文档与当前实现的一致性校验。
- 将证据链继续收束到代码、zap、迁移记录、协议实现本身。

### P2: 视需求投入

- Aputure ESP32 Runtime
- Aputure Commissioning Startup
- Aputure RS485 Lighting

目标:

- 决定是否需要新增独立文档域。
- 若不拆域，则至少完成集中式链路或问题域文档沉淀。

### P3: 后续专项治理

- Aputure Proto UDP

目标:

- 当 proto/Envelope/UDP frame 文档规模继续扩大时，再进行独立拆域和治理细化。

## 当前建议的管理动作

建议项目管理侧把后续动作压缩为 3 件事:

1. 先做 P0 三个 agent 的文档真实性审查，确保管理口径稳定。
2. 再做 P1 四个 agent 的专业域一致性复核，确保技术文档不漂移。
3. 最后再决定是否要为 Commissioning、RS485、Proto UDP 拆独立文档域。

## 维护约定

- 当新增 agent、拆分 docs 域、或调整 instruction 绑定时，应同步更新本文档。
- 当某个 agent 从“已注册”进入“已形成独立治理域”时，应同步提升其状态评级。
- 本文档关注项目治理状态，不替代各专业文档的技术细节。
