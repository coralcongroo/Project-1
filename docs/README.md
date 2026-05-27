# Documentation Index

更新时间: 2026-05-19

## 目录分组

当前 `docs/` 已按功能拆分为以下子目录：

- `ai/`: agent 使用说明与文档治理说明
- `architecture/`: 架构、模块分层、工程结构与高层设计
- `development/`: 构建、开发流程、发布检查、快速参考与变更记录
- `features/countdown/`: countdown 功能设计、集成与测试文档
- `matter/`: Matter/ZAP/CSA 相关文档
- `migration/`: 151_l3 迁移、对照表与迁移流程
- `network/`: MQTT、UDP、AMBL、主机侧协议与运维配置
- `analysis/`: 控制流、优化与性能分析

## Agent 管理映射

下表给出每个文档域的首选 agent，以及目录级 instruction 的绑定关系。

| 文档域 | 目录 | 首选 agent | 目录级 instruction |
|---|---|---|---|
| 根索引与总览 | `docs/README.md` | `Aputure Doc Maintainer` | `.github/instructions/docs-index.instructions.md` |
| AI 与治理 | `docs/ai/` | `Aputure Doc Maintainer` | `.github/instructions/docs-ai.instructions.md` |
| 架构与框架 | `docs/architecture/` | `Aputure Architecture Framework` | `.github/instructions/docs-architecture.instructions.md` |
| 构建与开发 | `docs/development/` | `Aputure Build Development` | `.github/instructions/docs-development.instructions.md` |
| Countdown 功能 | `docs/features/countdown/` | `Aputure Countdown Integration` | `.github/instructions/docs-features-countdown.instructions.md` |
| Matter / ZAP | `docs/matter/` | `Aputure Matter ZAP` | `.github/instructions/docs-matter.instructions.md` |
| 151_l3 迁移 | `docs/migration/` | `Aputure 151L3 Porting` | `.github/instructions/docs-migration.instructions.md` |
| 网络与运维 | `docs/network/` | `Aputure Network Ops` | `.github/instructions/docs-network.instructions.md` |
| 分析与优化 | `docs/analysis/` | `Aputure ESP32 Runtime` | `.github/instructions/docs-analysis.instructions.md` |

## 文档清单

### root

- `docs/README.md` -> `Aputure Doc Maintainer`

### ai

- `docs/ai/AI_AGENT_USAGE_GUIDE.md` -> `Aputure Doc Maintainer`
- `docs/ai/AGENT_PROGRESS_ROADMAP.md` -> `Aputure Doc Maintainer`

### architecture

- `docs/architecture/ARCHITECTURE.md` -> `Aputure Architecture Framework`
- `docs/architecture/CORE_CODE_FRAMEWORK.md` -> `Aputure Architecture Framework`
- `docs/architecture/PROJECT_STRUCTURE.md` -> `Aputure Architecture Framework`
- `docs/architecture/PROJECT_SUMMARY.md` -> `Aputure Architecture Framework`
- `docs/architecture/SmartLight_Architecture.md` -> `Aputure Architecture Framework`

### development

- `docs/development/BUILD.md` -> `Aputure Build Development`
- `docs/development/CHANGELOG.md` -> `Aputure Build Development`
- `docs/development/DEVELOPMENT_CHECKLIST.md` -> `Aputure Build Development`
- `docs/development/DEVELOPMENT_GUIDE.md` -> `Aputure Build Development`
- `docs/development/QUICK_REFERENCE.md` -> `Aputure Build Development`

### features/countdown

- `docs/features/countdown/COUNTDOWN_INTEGRATION_CHECKLIST.md` -> `Aputure Countdown Integration`
- `docs/features/countdown/COUNTDOWN_INTEGRATION_TEST.md` -> `Aputure Countdown Integration`
- `docs/features/countdown/COUNTDOWN_TASK_IMPLEMENTATION.md` -> `Aputure Countdown Integration`

### matter

- `docs/matter/EXTENDED_COLOR_LIGHT_ZAP_CHECKLIST.md` -> `Aputure Matter ZAP`
- `docs/matter/CSA_Docs/` -> `Aputure Matter ZAP`

### migration

- `docs/migration/151L3_CORRESPONDENCE_TABLE.md` -> `Aputure 151L3 Porting`
- `docs/migration/151L3_PIN_DEFINITION_TABLE.md` -> `Aputure 151L3 Porting`
- `docs/migration/151L3_PORTING_WORKFLOW.md` -> `Aputure 151L3 Porting`
- `docs/migration/LIGHTING_MIGRATION_FROM_151L3.md` -> `Aputure 151L3 Porting`

### network

- `docs/network/AMBL_FRAGMENT_PROTOCOL_DRAFT.md` -> `Aputure Network Ops`
- `docs/network/HOST_NETWORK_PROTOCOL_REQUIREMENTS.md` -> `Aputure Network Ops`
- `docs/network/MQTT_EMQX_OPS_TEMPLATE.md` -> `Aputure Network Ops`
- `docs/network/MQTT_SERVER_CONFIGURATION.md` -> `Aputure Network Ops`
- `docs/network/MQTT_UDP_PROTOCOL_SPEC.md` -> `Aputure Network Ops`
- `docs/network/NETWORK_ARCHITECTURE_CAPACITY.md` -> `Aputure Network Ops`
- `docs/network/NETWORK_MANAGEMENT.md` -> `Aputure Network Ops`

### analysis

- `docs/analysis/OPTIMIZATION_FIXES_2026_04_17.md` -> `Aputure ESP32 Runtime`
- `docs/analysis/control_flow_analysis.md` -> `Aputure Architecture Framework`
- `docs/analysis/task_optimization_analysis.md` -> `Aputure ESP32 Runtime`

## 使用约定

- 目录级 instruction 负责把同类文档拉到同一套维护规则下。
- `docs/README.md` 负责维护整个 docs 树的分类、agent 映射和 instruction 入口，不属于任何子目录时由根层 instruction 管理。
- agent 负责复杂任务时的上下文和判断边界；简单路径修正不需要强制切换 agent。
- 若某个文档未来跨域明显变化，应优先调整目录归类和 instruction，而不是只在文档正文里补说明。