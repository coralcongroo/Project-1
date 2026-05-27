# ESP32S3 智能灯具 - 网络管理与协议说明

## 一、目标与范围

本文档描述当前工程已支持的网络协议与网络管理策略。当前支持协议为：

- MQTT：云端控制与状态上报主通道
- Matter：智能家居生态互联通道
- UDP：局域网低延迟控制通道
- BLE：本地配网与离线控制通道

---

## 二、网络状态机

### 2.1 WiFi 管理

**WiFi 连接生命周期已统一归 Matter ConnectivityManager 管理**，包括：
- WiFi 栈初始化 (`esp_wifi_init`) — `ESP32Utils::InitWiFiStack()`
- STA 连接/配网 — `DriveStationState()` / `NetworkCommissioningDriver`
- 断线重连 — Matter 内置定时重连状态机

`ambient_wifi` 模块已精简为**纯状态观测层**，不进行任何 WiFi 操作：
- 监听 `IP_EVENT_STA_GOT_IP` / `IP_EVENT_STA_LOST_IP` 设置 EventGroup
- 对外提供 `ambient_wifi_connected()` / `ambient_wifi_wait_connected()`
- WiFi 省电控制 (`WIFI_PS_NONE`) 由 `main.cpp::on_ip_event()` 统一管理

### 2.2 系统级状态

```text
UNINITIALIZED
   ↓
SCANNING/CONNECTING (WiFi)
   ↓ 成功
DHCP
   ↓ 成功
ONLINE (MQTT + Matter + UDP + BLE)
   ↘ 异常
BLE_ONLY (仅 BLE 可用)
   ↘ 恢复 WiFi 后回到 ONLINE
```

### 2.2 核心状态说明

- UNINITIALIZED：网络组件未启动。
- SCANNING/CONNECTING：扫描并尝试连接已保存 WiFi。
- DHCP：等待获取 IPv4 地址。
- ONLINE：IP 就绪后启动 MQTT/Matter/UDP，BLE 持续广播。
- BLE_ONLY：IP 不可用或连接失败时降级，保留 BLE 与本地业务。

---

## 三、协议管理总览

| 协议 | 依赖网络 | 主要角色 | 典型数据类型 | 故障处理 |
|------|----------|----------|--------------|----------|
| MQTT | 需要 IP | 云端主控与回传 | 命令下发、状态上报、事件告警 | 自动重连、断线缓存、恢复后补发 |
| Matter | 需要 IP | 家居生态互联 | OnOff/Level/Color 等标准属性 | 保持 Fabric 状态，掉线后重入 |
| UDP | 需要 IP | 局域网低延迟 | 广播发现、快速控制、状态查询 | 端口重绑、轻量重试、无连接恢复 |
| BLE | 不依赖 IP | 本地接入与兜底 | 配网、设备发现、本地控制 | 始终保持可用，支持离线控制 |

---

## 四、协议详细说明

### 4.1 MQTT（云端主通道）

职责：
- 设备状态上报（开关、亮度、色温、模式等）
- 云端命令下发（控制指令、场景触发）
- 生命周期消息（在线/离线、异常告警）

实现细节：
- TLS 连接 (`mqtts://broker.emqx.io:8883`)，内置 EMQX Root CA
- 使用 QoS1 保障关键状态可达
- `disable_auto_reconnect = false` — ESP-IDF MQTT 库自动重连
- Client ID: `aputure-<wifi_sta_mac>`
- 订阅 4 个 topic: report/data, device/\<mac\>/down, group/down, all/down
- 状态变化通过 `state_manager` 回调自动触发上报（跳过 MQTT 来源避免回环）
- 连接/断开/错误事件通过 `NET_EVENT` 事件总线通知应用层

在线判定：
- `mqtt_agent_connected()` 为 true

故障恢复：
- WiFi 断连 → TCP 中断 → `MQTT_EVENT_DISCONNECTED`
- WiFi 恢复 → MQTT 库自动重连 → 重新订阅 + 上报当前状态

### 4.2 Matter（生态互联）

职责：
- 对接 Matter Fabric（如 HomeKit、Google Home）
- 接收标准 Cluster 控制并映射到统一状态模型
- 将本地状态变化映射为 Matter 属性更新
- **被动响应 WiFi 连接事件**（不主动控制，由 AppNetworkDelegate 策应）

实现细节：
- 通过 `CHIPDeviceManager::Init()` 启动，内部启动 `ConnectivityManagerImpl`
- `ConnectivityManagerImpl` 接收 `IP_EVENT_STA_GOT_IP` / `IP_EVENT_STA_LOST_IP` 事件
- `AppNetworkDelegate` 拦截连接事件，执行网络协议启动/停止编排
- WiFi 凭证由 `NetworkCommissioningDriver` 管理（KVS 持久化）
- BLE 仅用于配网 (`CONFIG_USE_BLE_ONLY_FOR_COMMISSIONING=y`)
- 使用 Minimal mDNS (`CONFIG_USE_MINIMAL_MDNS=y`)
- 支持 3 个 Fabric (`CONFIG_MAX_FABRICS=3`)
- 实际使用 3 个 Cluster: OnOff / LevelControl / ColorControl

在线判定：
- 设备处于有效 Fabric 上下文

故障恢复：
- Fabric 会话失效时触发重建
- 不阻塞其他协议的正常运行

### 4.3 UDP（局域网低延迟）

职责：
- 局域网实时灯光流接收（IPv4 组播）
- 帧超时检测与流过期标记

实现细节：
- 组播地址 `239.255.23.42`，端口 `5568`
- 自定义 AMBL 协议：magic `0x414D424C`，24 字节帧头，RGBA payload
- 最大帧 2048 字节，最大 500 通道
- `SO_RCVBUF=8192`，`SO_RCVTIMEO=200ms`
- 接收循环通过 `ambient_wifi_connected()` 判断退出条件
- WiFi 断开 → 超时后退出循环 → 关闭 socket → 等待 WiFi 恢复后重建
- 帧输出采用深度为 1 的覆盖队列（`xQueueOverwrite`），只保留最新帧

在线判定：
- `protocol_set_online(PROTOCOL_ID_UDP, true/false)` 由 `on_ip_event()` 管理

故障恢复：
- Socket 创建失败时指数退避重试（1s → 2s → 4s → ... → 10s）
- 帧超时（200ms 无数据）→ `ambient_output_mark_stale()`
- 当 Matter / MQTT / BLE / Button 等非 UDP 来源接管状态时，设备会先向最近一次 UDP 流发送端回发一个空 AMBL 帧作为停流信号，并同时向组播地址广播同样的停流帧；随后立即将本地输出标记为 stale

### 4.4 BLE（本地兜底通道）

职责：
- 首次配网（WiFi 凭据写入）
- 无 IP 时本地控制与状态读取
- 网络异常时提供最小可用控制面

实现建议：
- 在 ONLINE 与 BLE_ONLY 两种模式都保持广播。
- ONLINE 时可切换为只读/低频广播以节省功耗。
- BLE 控制写入后仍走统一状态分发链路。

在线判定：
- BLE 栈启动且广告任务正常。

故障恢复：
- BLE 异常重启不应影响 CPU1 本地业务。
- 配网成功后触发 WiFi 重连流程。

---

## 五、网络事件传播

关键网络事件通过自定义 `NET_EVENT` 事件总线（ESP-IDF 默认事件循环）传播到应用层：

| 事件 | 触发源 | 用途 |
|------|--------|------|
| `NET_EVENT_WIFI_CONNECTED` | `main.cpp::on_ip_event()` | IP 就绪通知 |
| `NET_EVENT_WIFI_RECONNECT_FAILED` | 保留（Matter 接管重连后暂不触发） | WiFi 连续重连失败 |
| `NET_EVENT_MQTT_CONNECTED` | `mqtt_agent.c` | MQTT 连接成功 |
| `NET_EVENT_MQTT_DISCONNECTED` | `mqtt_agent.c` | MQTT 断连 |
| `NET_EVENT_MQTT_ERROR` | `mqtt_agent.c` | MQTT 错误 |

事件定义：`components/framework/common/include/network_event.h`

---

## 六、协议启动顺序与协同

### 6.1 启动延迟策略

为了在配网/commissioning 期间保持 CPU 和内存的低开销，网络服务采用分阶段延迟启动：

| 服务 | 启动延迟 | 理由 |
|------|---------|------|
| UDP 实时流 | 500ms | 最低延迟，用于本地灯具控制快速响应 |
| RTC/SNTP 时间同步 | 1500ms | 依赖 DNS，由 NTP 完成 |
| MQTT 云端代理 | 20000ms | **关键延迟**：在此期间完成 Matter 配网和 commissioning 静默期，避免 CPU/内存争用；20s 足以让用户完成 HomeKit 配网 |

### 6.2 推荐启动顺序（IP 就绪后，由 AppNetworkDelegate::OnIPv4ConnectivityEstablished() 编排）

1. `esp_wifi_set_ps(WIFI_PS_NONE)` — 关闭 WiFi 省电，确保组播实时接收
2. `maybe_start_post_commission_services()` → 启动后台任务编排
3. **500ms 后**：`local_output_start_network_services()` → UDP 接收启动
4. **1500ms 后**：`app_rtc_init()` → 时间同步任务
5. **20000ms 后**：`mqtt_agent_init()` → MQTT 连接启动
6. BLE 持续广播（不依赖 IP，独立运行）

## 六.2、协议联动与回环避免

说明：
- 各协议间同步通过 StateManager + ProtocolDispatcher 完成
- **分发时跳过来源协议**，避免 A→B→A 的回环
- 示例：MQTT 下发命令 → state_manager → protocol_dispatch_state(source=MQTT) → 跳过 MQTT，仅推送给 Matter/UDP/BLE
- UDP 停流：当非 UDP 源接管时，会阻塞新的 UDP 帧接收，持续 `AMBIENT_FRAME_TIMEOUT_MS` (200ms) 后自动解除

---

## 六、健康检测与降级策略

### 6.1 周期检测项

- WiFi 连接状态与 RSSI
- IP 有效性（网关探活或等效机制）
- MQTT/Matter/UDP 在线标志
- BLE 广播状态

### 6.2 降级策略

- 条件：WiFi 断连或 IP 连续失效
- 动作：切换到 BLE_ONLY
- 保留能力：
  - CPU1 本地输入/输出/定时任务持续运行
  - BLE 本地控制可用
  - 状态变化本地生效，待网络恢复后再同步

### 6.3 恢复策略

- WiFi 恢复后进入 DHCP，成功后转 ONLINE。
- 按启动顺序恢复 MQTT/UDP/Matter。
- 将离线期间最新状态同步至在线协议。

---

## 七、网络信息结构建议

```c
typedef struct {
    bool mqtt_online;
    bool matter_online;
    bool udp_online;
    bool ble_online;
} protocol_status_t;
```

```c
typedef struct {
    network_state_t state;
    char ssid[32];
    char ip_addr[16];
    int32_t rssi;
    uint32_t ip_valid_count;
    protocol_status_t protocols;
} network_info_t;
```

---

## 八、排障建议

- MQTT 离线但本地可控：优先检查 Broker 可达性与证书。
- Matter 不可控但 MQTT 正常：检查 Fabric 会话与配网状态。
- UDP 丢包偏高：检查组播网络、AP 隔离、包长与发送速率。
- 仅 BLE 可用：说明设备处于 BLE_ONLY，优先恢复 WiFi/IP。

---

## 九、结论

当前工程网络管理采用“IP 优先 + BLE 兜底”的双层策略：

- 有 IP：MQTT/Matter/UDP/BLE 协同运行，满足云端、生态与局域网场景。
- 无 IP：自动降级 BLE_ONLY，保证设备可控与业务不中断。

该策略在复杂网络环境下兼顾了可用性、实时性与可维护性。
