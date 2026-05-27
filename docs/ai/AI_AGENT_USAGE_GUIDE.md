# Aputure IP Project Agent 使用说明

更新时间: 2026-05-19

## 目的

这份文档说明当前工程内置的 AI agent 和 prompt 模板分别适合做什么、什么时候该选哪个，以及怎样给它们提供输入，避免选错角色或把任务描述得过于宽泛。

## 文件位置

当前工作区的 agent 与 prompt 文件位于:

- `.github/agents/`
- `.github/prompts/`

索引文件位于:

- `.github/AGENTS.md`
- `docs/README.md`
- `docs/ai/AGENT_PROGRESS_ROADMAP.md`

根层治理文件位于:

- `.github/instructions/docs-index.instructions.md`

当前文档目录已按功能分组:

- `docs/README.md`
- `docs/ai/`
- `docs/architecture/`
- `docs/development/`
- `docs/features/countdown/`
- `docs/matter/`
- `docs/migration/`
- `docs/network/`
- `docs/analysis/`

## 快速使用方式

在 VS Code Copilot Chat 中有两种常用入口:

1. 直接切换 agent
   - 适合一整轮对话都围绕同一类任务展开。
   - 例如连续排查 commissioning、连续维护 ZAP 合规文档、连续分析 RS485 链路。

2. 运行 prompt 模板
   - 适合单次、边界明确的任务。
   - 例如“检查 Extended Color Light 合规”“分析一次 ESP32 崩溃”“更新迁移表”。

建议原则:

- 长链路排查选 agent。
- 单次标准任务选 prompt。

## 任务速查表

| 任务类型 | 优先 agent | 可直接用的 prompt | 说明 |
|---|---|---|---|
| 检查 Extended Color Light、endpoint、cluster、CSA 合规 | Aputure Matter ZAP | Check Extended Color Light | 以 `.zap`、`.matter`、CSA 文档为主证据 |
| 审核 ZAP 生成流程、wrapper、`ZAP_INSTALL_PATH`、reconfigure 要求 | Aputure Matter ZAP | Review ZAP Build Workflow | 适合 codegen、路径、wrapper、生成链问题 |
| 调 commissioning、CHIPoBLE、CASE、quiet window、SoftAP 冲突 | Aputure Commissioning Startup | Debug Commissioning Startup | 适合启动时序和配网阶段故障 |
| 追踪 RS485、Endpoint 2、PWM 映射、151_l3 灯控迁移 | Aputure RS485 Lighting | Trace RS485 Lighting Path | 适合本地灯控链和 RS485 回写分析 |
| 分析 stack overflow、Guru Meditation、TLS/heap/WDT | Aputure ESP32 Runtime | Analyze ESP32 Runtime Fault | 适合运行时稳定性与资源故障 |
| 更新架构、工程结构、框架分层、控制流文档 | Aputure Architecture Framework | 无 | 适合 `docs/architecture/` 与结构性分析文档 |
| 更新构建、开发、发布、清单、变更记录 | Aputure Build Development | 无 | 适合 `docs/development/` 下的执行型文档 |
| 更新 MQTT、UDP、EMQX、主机协议、AMBL 运维文档 | Aputure Network Ops | 无 | 适合 `docs/network/` 下的协议与运维文档 |
| 更新 Countdown 设计、集成、测试文档 | Aputure Countdown Integration | 无 | 适合 `docs/features/countdown/` 下的功能文档 |
| 更新迁移表、清单、总结文档 | Aputure Doc Maintainer | Update Migration Doc | 适合把文档和当前仓库现实对齐 |
| 处理 `~/git-code/151_l3` 的后续更新移植 | Aputure 151L3 Porting | Port 151L3 Update | 适合未来持续同步上游 legacy 工程改动 |
| 处理 `.proto` 文档数据帧、protobuf 字段语义、UDP 5568/5569 数据帧 | Aputure Proto UDP | Trace Proto UDP Frame | 适合 `AputureDeviceReference.proto` `Envelope`、旧 `Message.proto` 兼容、解析器与 UDP 帧处理链路 |

### 选择口诀

- 看 `.zap`、`.matter`、CSA 文档：选 Matter。
- 看 commissioning 日志和启动顺序：选 Commissioning。
- 看 `local_output`、`DeviceCallbacks`、RS485：选 RS485。
- 看 panic、heap、stack、TLS、WDT：选 Runtime。
- 看架构、工程结构、模块边界、控制流：选 Architecture Framework。
- 看构建、发布、清单、changelog：选 Build Development。
- 看 MQTT、UDP、EMQX、主机联调、AMBL：选 Network Ops。
- 看 Countdown 功能设计、测试、集成：选 Countdown Integration。
- 看 checklist、迁移表、总结文档：选 Doc。
- 看 `151_l3` 新提交或新改动怎么落到当前工程：选 151L3 Porting。
- 看 `.proto`、protobuf 字段、UDP 帧、`message_proto`：选 Proto UDP。

## Agent 总览

### 1. Aputure Matter ZAP

适用场景:

- `.zap`、`.matter`、endpoint device type、cluster 选择、CHIP codegen
- `ZAP_INSTALL_PATH`、wrapper、生成路径、`idf.py reconfigure build`
- `docs/matter/CSA_Docs` 对照、Extended Color Light 合规

最适合的输入:

- 一个 `.zap` 文件路径
- 某个 endpoint 或 cluster 的变更点
- 构建报错、codegen 报错、Device Type Compliance 报错

不适合的任务:

- ESP32 栈溢出、TLS 内存、WDT 这类运行时问题
- RS485 业务链路和 151_l3 迁移细节

典型提问:

- “检查当前 zap 里 Endpoint 1/2 的 Extended Color Light 是否合规”
- “为什么加了 Scenes Management 后还要 reconfigure build”
- “wrapper 里的 ZAP_INSTALL_PATH 现在是否正确”

### 2. Aputure Commissioning Startup

适用场景:

- Matter commissioning
- CHIPoBLE、CASE、PacketBuffer 耗尽
- quiet window、BLE deinit、分阶段启动
- SoftAP 与 BLE-only commissioning 冲突

最适合的输入:

- commissioning 阶段日志
- CASE/Sigma 错误、BLE ACK 超时、heap fail 日志
- 某个服务启动顺序的改动说明

不适合的任务:

- ZAP 勾选结果核对
- 单纯文档维护
- 一般性的 RS485 逻辑问题

典型提问:

- “为什么 commissioning 后刚起 MQTT 就 CASE 失败”
- “quiet window 结束前启动哪些服务最危险”
- “为什么开启 legacy bluetooth 后 BLE_INIT 内存不足”

### 3. Aputure RS485 Lighting

适用场景:

- RS485 主从链路
- Endpoint 2 同步
- `local_output`、`DeviceCallbacks`、`app_rs485_master`
- PWM 槽位映射、`Factory_RGBWW`
- 151_l3 迁移、`point_light_firmware`

最适合的输入:

- 要追踪的一条灯控路径
- 某个 endpoint 的状态回写问题
- 151_l3 和当前工程某个文件或功能点的差异

不适合的任务:

- 纯 ZAP/CSA 合规
- 单纯栈/堆/TLS 类运行时故障

典型提问:

- “Endpoint 2 的状态是怎样从 RS485 回写到 Matter 的”
- “LIGHT_MODE_PWM 最后走的是哪条 RS485 命令”
- “151_l3 里的某个 PWM 行为当前工程有没有迁”

### 4. Aputure ESP32 Runtime

适用场景:

- stack overflow
- ISR float 崩溃
- heap fragmentation
- TLS 分配失败
- WDT、main 任务大栈数组、任务栈大小问题

最适合的输入:

- panic 日志
- Guru Meditation 日志
- mbedtls/TLS 错误、WDT 日志
- 某个任务的栈/堆变化说明

不适合的任务:

- ZAP 合规
- 文档清单维护
- 一般的 commissioning 时序问题（除非已经明确是资源故障）

典型提问:

- “这个 Coprocessor exception 为什么会落在 dev_lamp 定时器回调”
- “main 任务是不是又被 HTTP JSON 大栈数组打爆了”
- “TLS 握手失败是总 heap 不够还是连续块不够”

### 5. Aputure Doc Maintainer

适用场景:

- 迁移表
- ZAP checklist
- 集成检查清单
- 项目总结、状态矩阵、对应表
- 需要把文档和当前代码现实对齐的任务

最适合的输入:

- 目标文档路径
- 本次变更涉及的模块
- 需要更正的旧结论

不适合的任务:

- 直接做运行时调试
- 替代技术分析 agent 做底层根因排查

典型提问:

- “根据当前仓库状态更新迁移对照表”
- “把 Extended Color Light 清单改成当前 zap 快照”
- “把项目总结里过时的说法纠正掉”

### 6. Aputure 151L3 Porting

适用场景:

- `~/git-code/151_l3` 未来继续更新
- 需要把上游 legacy 工程的新改动评估后移植到当前工程
- 需要判断某个 legacy 更新当前是否已存在、是否被当前工程增强、是否还缺失
- 需要在保持当前 framework 结构不回退的前提下做最小移植

最适合的输入:

- `151_l3` 的文件路径
- 某个 commit、变更点、功能描述
- 想确认的“当前工程是否已经同步”问题

不适合的任务:

- 单纯追踪当前仓库内部 RS485 路径但没有上游对照需求
- 单纯文档润色
- 单纯运行时故障分析

典型提问:

- “151_l3 新改了 app_rs485_master，这部分当前工程要不要同步”
- “帮我把 151_l3 这个 PWM 行为移植到当前工程”
- “这个 legacy 更新在当前工程里是已对齐、已增强还是还没迁”

配套流程文档:

- `docs/migration/151L3_PORTING_WORKFLOW.md`

### 7. Aputure Proto UDP

适用场景:

- `.proto` 文档数据帧
- `AputureDeviceReference.proto` `Envelope` 与旧 `Message.proto` 兼容关系
- UDP 5568/5569 数据帧
- `message_proto` 解析/编码
- proto 帧内 `packets` 与 BLE mesh 包桥接

最适合的输入:

- 某个 `.proto` 文件路径
- 某个字段或一帧 UDP payload
- 想确认的“当前到底走哪份 proto”“当前字段是否真的生效”问题

不适合的任务:

- 纯 Matter ZAP 合规
- 纯 RS485 灯控迁移
- 纯运行时崩溃分析

典型提问:

- “当前 UDP 控制帧到底以哪份 proto 为准”
- “RawBleControl.packets 在代码里最后怎么落到设备控制”
- “AputureDeviceReference.proto 里的字段哪些是参考，哪些已经进入当前实现”

### 8. Aputure Architecture Framework

适用场景:

- `docs/architecture/` 下的架构、框架、工程结构文档
- 控制流说明和模块边界核对
- 需要把高层设计描述和当前代码入口对齐的任务

最适合的输入:

- 一个架构文档路径
- 想核对的模块关系或调用链
- 某个目录调整后需要同步的结构说明

不适合的任务:

- 纯运行时崩溃分析
- 纯协议字段语义核对

典型提问:

- “帮我把 PROJECT_STRUCTURE 和当前仓库结构重新对齐”
- “这份架构文档里哪些模块边界已经过时”

### 9. Aputure Build Development

适用场景:

- `docs/development/` 下的构建、开发、发布文档
- checklist、changelog、快速参考维护
- 需要核对命令、配置项、发布步骤是否还有效的任务

最适合的输入:

- 一个开发或构建文档路径
- 变更过的构建命令、脚本或配置项
- 想核对的发布流程或检查项

不适合的任务:

- 纯架构设计核对
- 纯功能协议分析

典型提问:

- “更新 BUILD 和 DEVELOPMENT_GUIDE，让命令跟当前仓库一致”
- “把 changelog 和发布 checklist 按当前流程修正”

### 10. Aputure Network Ops

适用场景:

- `docs/network/` 下的 MQTT、UDP、EMQX、主机协议与运维文档
- 需要区分协议真值文档、运维模板、草案说明的任务
- 网络管理与容量说明更新

最适合的输入:

- 一个网络文档路径
- 一条 MQTT/UDP 行为变更说明
- broker、TLS、主题或主机联调的约束问题

不适合的任务:

- 纯 Matter ZAP 合规
- 纯本地灯控迁移

典型提问:

- “把 MQTT 配置文档和当前 TLS 开关逻辑对齐”
- “确认运维模板和协议规范之间哪些字段不能写死”

### 11. Aputure Countdown Integration

适用场景:

- `docs/features/countdown/` 下的 Countdown 设计、实现、测试文档
- 倒计时功能的联调清单和验证步骤更新
- 实现说明与测试说明之间的一致性检查

最适合的输入:

- 一个 countdown 文档路径
- 倒计时接口或行为的变更点
- 想核对的测试步骤或边界条件

不适合的任务:

- 泛化的仓库级文档治理
- 无 countdown 上下文的运行时崩溃分析

典型提问:

- “把 countdown 的实现文档和测试清单统一一下”
- “这份倒计时联调步骤里哪些已经和当前实现不一致”

## Prompt 模板总览

当前可直接使用的 prompt 模板如下:

### 1. Check Extended Color Light

用途:

- 检查当前 Extended Color Light 的 `.zap` 配置
- 对照 `docs/matter/CSA_Docs`
- 更新 `docs/matter/EXTENDED_COLOR_LIGHT_ZAP_CHECKLIST.md`

适合输入:

- “检查 Endpoint 1 和 2 的 Extended Color Light 合规性”
- “我刚改了 Level Control，帮我重看清单”

### 2. Debug Commissioning Startup

用途:

- 分析 commissioning、BLE、CASE、quiet window、分阶段启动问题

适合输入:

- commissioning 日志
- CASE 错误文本
- 服务启动顺序描述

### 3. Trace RS485 Lighting Path

用途:

- 追踪 RS485 灯控路径
- 看状态/命令如何在 `local_output`、`DeviceCallbacks`、`app_rs485_master` 间流动

适合输入:

- “帮我追一条 Endpoint 2 -> RS485 -> Matter 的路径”
- “Factory_RGBWW 到本地 PWM 是怎么映射的”

### 4. Analyze ESP32 Runtime Fault

用途:

- 分析崩溃、栈、堆、TLS、WDT、ISR 问题

适合输入:

- panic log
- Guru Meditation
- TLS 报错

### 5. Update Migration Doc

用途:

- 更新迁移表、对照表、项目总结、集成检查清单

适合输入:

- 文档路径
- 本次代码或配置改动范围

### 6. Review ZAP Build Workflow

用途:

- 审核 ZAP 生成流程
- 核对 wrapper、`ZAP_INSTALL_PATH`、路径解析、reconfigure 要求

适合输入:

- ZAP 生成命令
- wrapper 脚本
- codegen 相关构建失败日志

### 7. Port 151L3 Update

用途:

- 对比 `~/git-code/151_l3` 的新增或修改
- 判断当前仓库是否已吸收该行为
- 在需要时做最小、保留框架的移植

适合输入:

- `151_l3` 文件路径
- commit 描述
- 想同步的具体功能点

### 8. Trace Proto UDP Frame

用途:

- 追踪 `.proto` 文档数据帧
- 追踪 UDP payload 如何进入 `message_proto` 和 `ambient_command`
- 判断当前字段语义是 typed control 还是 BLE packet bridging

适合输入:

- 某个 UDP 数据帧
- 某个 `.proto` 字段
- 某条 `Envelope -> message_proto -> ambient_command` 路径

## 如何选 agent

如果一个任务跨多个方向，优先按“主证据来源”来选:

1. 以 `.zap`、`.matter`、CSA 文档为主证据：选 `Aputure Matter ZAP`
2. 以 commissioning 日志、启动顺序、BLE/CASE 为主证据：选 `Aputure Commissioning Startup`
3. 以 `local_output`、`DeviceCallbacks`、RS485 协议或 151_l3 对照为主证据：选 `Aputure RS485 Lighting`
4. 以 panic、堆、栈、TLS、WDT 为主证据：选 `Aputure ESP32 Runtime`
5. 以现有文档和仓库现实不一致为主问题：选 `Aputure Doc Maintainer`
6. 以 `~/git-code/151_l3` 的新改动为源头、需要决定如何落到当前工程：选 `Aputure 151L3 Porting`
7. 以 `.proto`、protobuf 字段、UDP 数据帧和解析链为主证据：选 `Aputure Proto UDP`

## 推荐输入方式

为了让 agent 更快进入正确路径，建议在提问时至少给出以下一种输入:

- 目标文件路径
- 报错日志
- 目标 endpoint / cluster / task 名称
- 你想要的结果形式

建议示例:

- “用 Aputure Matter ZAP 检查这个 zap 的 Endpoint 2 Level Control 是否满足 CSA 1.5”
- “用 Aputure RS485 Lighting 追踪 app_rs485_master 到 DeviceCallbacks 的回写链”
- “用 Aputure ESP32 Runtime 分析这段 Guru Meditation 日志”
- “用 Aputure Architecture Framework 重新核对 docs/architecture/PROJECT_STRUCTURE.md 和当前目录树”
- “用 Aputure Network Ops 更新 docs/network/MQTT_SERVER_CONFIGURATION.md 并检查和协议文档的一致性”
- “用 Aputure Countdown Integration 检查 docs/features/countdown/COUNTDOWN_INTEGRATION_TEST.md 是否还匹配当前实现”
- “用 Aputure Doc Maintainer 更新 docs/migration/151L3_CORRESPONDENCE_TABLE.md”
- “用 Aputure 151L3 Porting 对比这个 151_l3 新改动是否需要移植”
- “用 Aputure Proto UDP 追踪这个 Envelope 数据帧在 UDP 通道里的处理路径”

## 仓库特定注意事项

- 与 ZAP 相关的任务，当前仓库的事实来源是 checked-in 的 `.zap` 文件，而不是旧 checklist。
- 与 RS485 灯控相关的任务，当前真实桥接点是 `components/app/local_output`，不是历史的 `main/app.c`。
- 与 `151_l3` 更新移植相关的任务，不要只按同名文件覆盖，必须先确认当前工程里的活跃落点。
- 与 `.proto`/UDP 数据帧相关的任务，要先区分当前对外格式 `AputureDeviceReference.proto` `Envelope`、当前控制语义 `RawBleControl.packets`，以及旧 `Message.proto` 的兼容接收角色，不能再把 `Message.proto` 写成当前活跃链。
- 与 commissioning 相关的任务，不要忽略 quiet window、BLE deinit 和 legacy bluetooth 冲突。
- 与运行时稳定性相关的任务，不要把 includePath 噪声误当成真实编译或运行时错误。

## 建议维护方式

如果后面仓库重点发生变化，建议按以下顺序维护:

1. 先更新对应 agent 的 `description` 和事实约束。
2. 再更新 prompt 模板里的任务描述。
3. 最后更新 `.github/AGENTS.md` 和本手册。

这样可以避免“agent 能力已经变了，但索引和用法文档还停留在旧版本”。