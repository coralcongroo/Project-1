# 当前网络架构与功能/负载能力说明

## 1. 文档目的

本文档面向当前代码现状，说明：

- 网络链路如何启动与协同
- 当前可实现的功能边界
- 现阶段可承载的典型负载与建议阈值

说明口径：以当前主干代码实现与配置为准，不包含尚未接入主构建的历史模块。

---

## 2. 当前网络架构（运行视角）

### 2.1 启动主链路

系统在 `main/main.cpp` 中完成核心初始化：

1. 初始化状态与分发层（`state_manager` / `ipc_manager` / `protocol_dispatcher`）。
2. 注册 IP 事件回调。
3. Matter 通过 `ESP32Utils::InitWiFiStack()` 初始化 WiFi 栈。
4. `local_output_init()` 启动 CPU1 业务，`ambient_wifi_init_sta()` 仅注册 IP 事件监听。
5. `CHIPDeviceManager::Init()` 启动 Matter，由 Matter 管理 WiFi 连接。
6. 在 `IP_EVENT_STA_GOT_IP` 触发后依次启动：
   - 关闭 WiFi 省电 (`WIFI_PS_NONE`)
   - RTC/SNTP 同步任务
   - UDP 接收/输出服务
   - MQTT Agent
7. 丢失 IP（`IP_EVENT_STA_LOST_IP`）时，UDP 协议在线状态被置离线。

该流程体现的是“IP 就绪后再启动上层网络协议”，避免无 IP 阶段重复失败重试。

### 2.2 协议与职责分层

- Wi-Fi/IP 层：连通性前提，**统一由 Matter ConnectivityManager 管理**。
- `ambient_wifi` 模块：纯 IP 事件观测层，为应用层提供 `connected()`/`wait_connected()` API。
- UDP 实时流层：局域网实时帧接收，驱动本地输出。
- MQTT 云通道层：云端命令下发与状态上报（JSON）。
- Matter 生态层：保持 Matter 在线能力（与状态管理器协同）。
- BLE 本地层：配网与离线本地控制兜底。

### 2.3 状态同步机制

当前工程的多协议协同通过统一状态源实现：

- 外部命令进入后先更新 `state_manager`
- 再通过 `protocol_dispatcher` 对外扩散
- MQTT 回写场景会跳过同源，避免环路

这意味着网络协议本身不直接互相写状态，降低冲突概率。

---

## 3. 已落地功能（当前可实现）

### 3.1 UDP（局域网实时流）

已实现：

- IPv4 组播接收
- 固定协议头校验（magic/version/header/payload/channel）
- 最新帧覆盖策略（队列深度 1）
- 输出链路调用本地灯光渲染
- 帧超时判定（超时后标记 stale）

关键实现参数（代码与配置）：

- 组播地址：`239.255.23.42`
- 端口：`5568`
- 单帧最大尺寸：`2048 bytes`
- 最大通道数：`500`（RGBA，4 字节每通道）
- socket 接收缓冲：`4 * MAX_FRAME_SIZE = 8192 bytes`
- 帧超时：`200 ms`
- 接收任务栈：`10 KB`
- 输出任务栈：`10 KB`
- 接收/输出任务核心：双核场景默认绑在 Core 1

### 3.2 MQTT（云端控制与回传）

已实现：

- TLS 连接（可用内置 EMQX Root CA）
- 自动重连（`disable_auto_reconnect=false`）
- 主题订阅与命令解析（JSON）
- 状态变更回调后自动上报（QoS1）
- 支持设备/组播/全体下行主题

关键特征：

- 默认协议：MQTT 3.1.1（可切换 v5）
- 上报与下行均按 QoS1 路径使用
- 当前消息体为 JSON，包含开关、亮度、色彩模式及版本时间戳等字段

### 3.3 Matter

已具备：

- Matter 栈初始化与在线状态管理联动
- 与统一状态模型协同更新

相关网络配置（当前 sdkconfig）：

- `CONFIG_NUM_TCP_ENDPOINTS=8`
- `CONFIG_NUM_UDP_ENDPOINTS=8`

### 3.4 BLE

已具备：

- NimBLE 基础能力（配网/连接/广播）
- 与无 IP 场景的本地控制兜底角色

相关配置（当前 sdkconfig）：

- `CONFIG_BT_NIMBLE_ATT_PREFERRED_MTU=256`
- `CONFIG_BT_NIMBLE_MAX_CONNECTIONS=3`

---

## 4. 当前负载能力评估（工程可落地口径）

> 说明：以下为“当前实现可稳定推进的建议值”，不是极限压测峰值。

### 4.1 UDP 实时流负载

基于 `MAX_FRAME_SIZE=2048`、`RCVBUF=8192`、队列覆盖策略（深度1）可得：

- 推荐长期负载：
  - `512 bytes / 20 ms`（50 fps）
  - 吞吐约 $512 \times 50 = 25600\ \text{B/s} \approx 25\ \text{KB/s}$
- 可接受较高负载（需网络质量较好）：
  - `2 KB / 20 ms`
  - 吞吐约 $2048 \times 50 = 102400\ \text{B/s} \approx 100\ \text{KB/s}$

风险点：

- 组播网络有天然丢包与抖动风险
- 当前策略是“只保留最新帧”，会主动丢弃积压帧以换低延迟
- 当突发流量超过 socket 缓冲承载时，会出现跳帧但系统可继续运行

结论：

- 对灯光实时控制场景，`512B/20ms` 属于稳态可用区间。
- `2KB/20ms` 可运行，但对 AP、局域网拥塞和发送端抖动更敏感。

### 4.2 MQTT 业务负载

当前路径适合：

- 低到中频控制命令（设备控制类）
- 中低频状态上报（状态变化触发上报）

建议：

- 维持“事件触发上报 + 必要心跳”而非高频全量上报
- 大负载遥测建议拆分主题与字段，避免单 topic 高并发堆积

### 4.3 多协议并行负载

当前架构下，多协议并行主要受以下资源约束：

- Wi-Fi 空口竞争（MQTT + Matter + UDP + BLE）
- lwIP UDP PCB 与接收邮箱配置
- 任务栈与调度时延

当前配置要点：

- `CONFIG_LWIP_MAX_UDP_PCBS=16`
- `CONFIG_LWIP_UDP_RECVMBOX_SIZE=6`
- `CONFIG_ESP_IPC_TASK_STACK_SIZE=2048`

建议：

- 保持 UDP 流量实时优先，MQTT 上报做节流
- 长时间高并发前先做 24h 稳定性压测（丢包率、任务水位、重连行为）

---

## 5. 能力边界与已知限制

- UDP 协议当前是固定帧头 + RGBA payload，适配实时灯光流，不适合超大报文业务。
- 输出侧采用“最新帧覆盖”策略，保证低延迟但不保证帧完整到达率。
- MQTT 目前采用 JSON 命令模型，易扩展但消息体较二进制协议更重。
- BLE 同时承担兜底控制能力，在弱网下应避免与高频 UDP 长时并发压满空口。

---

## 6. 版本化建议（下一步）

建议把网络能力分成明确等级，便于测试和交付：

- Level A（默认交付）：`UDP 512B/20ms + MQTT 控制/回传`
- Level B（增强模式）：`UDP 2KB/20ms`（需通过网络质量门限）
- Level C（压测模式）：多协议并行 soak test（24h）

配套指标建议：

- UDP 有效帧率（fps）
- 端到端控制时延（P50/P95）
- MQTT 重连次数与恢复时间
- 任务栈最小余量（高水位）

---

## 7. 相关代码定位

- 启动与 IP 事件联动：`main/main.cpp`
- WiFi 状态观测：`components/network/cmd_wifi/ambient_wifi.c`
- UDP 服务启动入口：`main/app/local_manager.c`
- UDP 接收：`components/network/cmd_wifi/ambient_receiver.c`
- UDP 协议解析：`components/network/cmd_wifi/ambient_protocol.c`
- UDP 输出：`components/network/cmd_wifi/ambient_output.c`
- UDP 参数配置：`components/network/cmd_wifi/include/ambient_config.h`
- MQTT Agent：`components/network/mqtt_agent/src/mqtt_agent.c`
- MQTT 可配置项：`main/Kconfig.projbuild`

---

## 8. 总结

当前工程网络架构已经具备“可上线联调”的基础闭环：

- 有 IP：MQTT + Matter + UDP 协同，BLE 同时可用
- 无 IP：BLE 作为本地兜底通道
- 负载层面：实时控制推荐 `512B/20ms`，高负载 `2KB/20ms` 需网络条件保障

该架构的核心优势是低延迟优先与状态统一管理，适合智能灯具场景的实时控制与多协议共存。