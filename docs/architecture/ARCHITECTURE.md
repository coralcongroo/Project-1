# 系统架构设计文档

> **文档版本**：2.0  
> **最后更新**：2026-04-17  
> **状态**：✅ 实装完成 (RTC 网络时间同步集成验证)  
> **受众**：架构师、核心开发工程师、系统集成工程师

---

## 1. 系统概览

### 1.1 设计目标

Aputure IP Project 是一套双核隔离的智能灯具系统，在保证本地响应时间的同时，支持多种网络协议无缝协作，并具备优雅的离线降级能力。

**核心目标**：
- ✅ **本地无延迟**：CPU1 本地业务 ≤ 16ms 响应时间
- ✅ **网络鲁棒**：无网络时 BLE 仍可控制，数据不丢失
- ✅ **多协议同步**：防环路、防冲突、无数据不一致
- ✅ **可扩展性**：易于添加协议、业务模块、外设驱动

### 1.2 系统分层

```
┌────────────────────────────────────────────────────────────┐
│              应用层 (Application)                           │
│  Matter CLI | MQTT Commands | UDP Local | BLE Control      │
├────────────────────────────────────────────────────────────┤
│              协议层 (Protocol)                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Matter Fabric | MQTT Client | UDP Receiver | BLE Gate│  │
│  │ (CPU0 - 网络核心)                                    │  │
│  └──────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────┤
│              中间件层 (Middleware)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ StateManager | ProtocolDispatcher | IPC Manager      │  │
│  │ (跨核通信、状态管理、防重复)                          │  │
│  └──────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────┤
│              驱动层 (Driver)                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ LocalOutput | DevLamp | RS485Master | ...            │  │
│  │ (CPU1 - 业务隔离)                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ GPIO | SPI | UART | Timer | PWM | ADC               │  │
│  │ (FreeRTOS + ESP-IDF HAL)                             │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## 2. CPU 的双核分离架构

### 2.1 核心职责划分

```
┌─────────────────────────────────────┬──────────────────────────────┐
│        CPU0 - 网络核心              │     CPU1 - 业务隔离核         │
├─────────────────────────────────────┼──────────────────────────────┤
│ 职责：                              │ 职责：                        │
│ • WiFi 驱动与连接管理               │ • 本地输入采集                │
│ • Matter ZCL 处理、Fabric 管理       │ • 输出驱动控制 (LED/PWM)     │
│ • MQTT 连接保活、消息收发            │ • 定时任务执行                │
│ • UDP 多播接收与分发                 │ • 灯光动画计算                │
│ • BLE 广告与连接管理                │ • 本地数据库维护              │
│ • 协议状态监测与故障恢复            │ • RS485/Modbus 从机管理      │
│ • DNS-SD/mDNS 发布                  │ • 本地存储 (NVS)              │
│ • 网络时间同步 (RTC/SNTP)           │                              │
│                                     │                              │
│ 性能特征：                          │ 性能特征：                    │
│ • 高并发、高延迟容许               │ • 实时性要求高、单线程       │
│ • 秒级或分钟级任务                  │ • 毫秒级实时响应              │
│ • 网络隔离风险                      │ • 本地隔离、崩溃影响小       │
└─────────────────────────────────────┴──────────────────────────────┘
```

### 2.2 核间通信 (IPC)

**通道**：FreeRTOS 消息队列

**协议**：
```c
typedef struct {
    uint32_t type;        // 消息类型 (COMMAND/STATUS/RESPONSE)
    uint32_t priority;    // 优先级 (0=最低, 31=最高)
    uint32_t timestamp;   // 消息时间戳 (毫秒)
    void* payload;        // 数据指针
    uint16_t payload_len; // 数据长度
} ipc_message_t;
```

**典型流程**：
```
CPU0: Matter 命令 "设置亮度 128"
  ↓
IPC.send(TYPE_SET_LEVEL, priority=10, payload=128)
  ↓
CPU1: 从 IPC 队列接收消息
  ↓
CPU1: 计算 PWM， 设置硬件
  ↓
CPU1: 更新 StateManager (亮度 = 128, version++, last_source=MATTER)
  ↓
IPC.send(TYPE_STATUS_UPDATE, status_packet)
  ↓
CPU0: 接收状态更新，广播给其他协议
  ↓
MQTT: publish state/aputure/level=128
UDP:  broadcast status
Blue: send notification
```

---

## 3. 状态管理系统 (StateManager)

### 3.1 数据模型

```c
typedef struct {
    // 电源状态
    bool power_on;                    // 0=关, 1=开
    uint8_t matter_level;             // Matter 亮度 (0-254)
    
    // 灯光颜色
    light_color_t color;              // HSI / XY / CCT 三种模式
    
    // 元数据
    uint64_t version;                 // 状态版本号 (每改一次++)
    uint32_t last_update_time;        // 最后更新时间戳 (毫秒)
    uint8_t last_source;              // 更新来源 (MATTER/MQTT/UDP/BLE/LOCAL)
    
    // 模式
    uint8_t mode;                     // 工作模式 (普通/定时/动画)
    
    // 扩展
    uint32_t crc32;                   // CRC 校验
} device_state_t;
```

### 3.2 版本号机制（防重复）

```
初始状态: version = 100, last_source = NONE, timestamp = t0

事件1: MQTT 消息 "set_level 200"
  ➜ version = 101, last_source = MQTT, timestamp = t1

事件2: Matter 同步状态到 StateManager
  - 收到 version = 101
  - 本地 version 也是 101
  - ❌ 跳过（防反馈）

事件3: 用户按键 "提升亮度 10"
  ➜ version = 102, last_source = LOCAL, timestamp = t2

事件4: MQTT 客户端读取最新状态
  - 看到 version = 102, last_source = LOCAL
  - ✅ 发送更新到云端
```

### 3.3 持久化

使用 NVS (Non-Volatile Storage) 定期保存关键状态：
- 功率状态 (开/关)
- 灯光颜色 (HSI/XY/CCT 完整参数)
- 配置 (WiFi SSID/密码、时区等)

---

## 4. 协议分发系统 (ProtocolDispatcher)

### 4.1 信息流向

```
各协议协程
  ├─ Matter ZCL Handler
  ├─ MQTT Command Receiver
  ├─ UDP Local Listener
  ├─ BLE GATT Attribute
  └─ Local Keypad Input
      ↓
ProtocolDispatcher 路由层
      ↓
  1. 检查版本号与来源（防环路）
  2. 构建统一命令格式
  3. 调用 StateManager 更新
  4. 获取最新状态
      ↓
状态变化事件抛出
      ↓
所有协议均收到新状态
      ↓
协议特定格式编码并发送
  ├─ Matter: attribute report
  ├─ MQTT: publish state/xxx
  ├─ UDP: multicast packet
  ├─ BLE: GATT notify
  └─ 无网络模式: 只更新本地 DB
```

### 4.2 防环路机制

```
规则 1: 跳过来源协议
  if (msg.source == MQTT)
      skip_protocol_send(MQTT);  // MQTT 命令不反馈给 MQTT

规则 2: 版本号一致性检查
  new_version = local_version + 1 ?
  if (new_version != local_version + 1)
      log_warn("version mismatch");
      return;

规则 3: 时间戳检测异常
  if (msg.timestamp > now + 1000)  // 时间戳超前 > 1s
      log_error("suspicious timestamp");
      return;
```

---

## 5. 网络时间同步 (RTC 与 SNTP)

### 5.1 启动时序（IP-Ready-Gate）

```
系统启动
  ↓
WiFi 初始化
  ↓
Matter 服务启动
  ↓
WiFi 扫描 & 连接
  ↓
⏰ IP_EVENT_STA_GOT_IP 触发
  ├─ ✅ app_rtc_init() 启动 (优先级最高)
  │   ├─ 地理定位 (IP-API) → 获取国家/城市/坐标
  │   ├─ 时区查表 → 获取 TZ string (e.g., "CST-8")
  │   ├─ SNTP 初始化 → asia.pool.ntp.org, ntp.aliyun.com
  │   ├─ SNTP 同步 → 更新系统时间 (自动写入 RTC)
  │   └─ 回调 state_store 持久化时间数据
  │
  ├─ ✅ local_output_start_network_services() (CPU1 UDP)
  │
  └─ ✅ mqtt_agent_init() (MQTTS 连接)
```

### 5.2 时间同步工作流

```
RTC 任务                SNTP 服务              系统时钟
  ├─ 创建 manager
  ├─ 启动任务event loop
  │
  ├─ 等待 WiFi 就绪
  │
  ├─ 地理定位请求 ────────────────┐
  │                               │
  │ 国家: China, 城市: Shenzhen   │
  │ 时区: Asia/Shanghai           │
  │                               │
  ├─ SNTP 初始化                  │
  │  └─ 配置服务器 ────────────────────────────→ SNTP CLIENT
  │                                             │
  ├─ SNTP 同步请求 ──────────────────────────→ 接收 NTP 包
  │                                             │
  │                                      计算时间偏移
  │                                             │
  │                      时间数据 ───────────────↓
  │                      (UTC 秒数 + 毫秒)
  │
  ├─ 系统时间更新 ←──────────────────────────┘
  │  └─ settimeofday() / clock_settime()
  │  └─ 硬件 RTC 获得准确值
  │
  ├─ 状态持久化
  │  ├─ year, month, day, hour, min, sec → NVS
  │  └─ timezone string → NVS
  │
  ├─ Matter 读取准确时间
  │  └─ system_clock::now() 返回正确 UTC
  │
  └─ RTC 任务完成后清理并等待下次同步
```

### 5.3 时区覆盖表

```
国家/地区              时区 String          UTC 偏移
────────────────────────────────────────────────
China                  CST-8                UTC+8
USA - Eastern          EST5EDT              UTC-5/4
USA - Central          CST6CDT              UTC-6/5
USA - Mountain         MST7MDT              UTC-7/6
USA - Pacific          PST8PDT              UTC-8/7
Europe - London        GMT0BST              UTC+0/1
Europe - Paris         CET-1CEST,M3.5.0,M10.5.0  UTC+1/2
Japan                  JST-9                UTC+9
Singapore              SGT-8                UTC+8
```

### 5.4 故障处理

```
场景 1: 地理定位失败
  → 使用默认时区 (UTC+0 或预设 timezone)
  → 继续 SNTP 同步
  → 日志: "geo_location failed, using default tz"

场景 2: SNTP 首次同步超时
  → 重试 3 次，间隔 1s
  → 若都失败，则保持系统当前时间（无法校正）
  → 日志: "SNTP sync failed after 3 retries"

场景 3: 失去 IP 后重连
  → 记录上一次成功同步的时间
  → 重连成功可选择再次同步
  → 日志: "resuming RTC sync after IP regain"
```

---

## 6. 启动流程与状态转迁

### 6.1 完整启动类图

```
app_main()
  │
  ├─→ logger_init()
  │
  ├─→ esp_event_loop_create_default()
  │
  ├─→ state_manager_init()
  │    └─ 从 NVS 恢复上次状态
  │
  ├─→ ipc_manager_init()
  │    └─ 创建 CPU0 ←→ CPU1 消息队列
  │
  ├─→ protocol_dispatcher_init()
  │    └─ 注册各协议的 command/status 处理函数
  │
  ├─→ esp_event_handler_register(IP_EVENT, on_ip_event)
  │    └─ 监听 IP 就绪事件
  │
  ├─→ esp_event_handler_register(IP_EVENT, on_ip_lost)
  │    └─ 监听 IP 丢失事件
  │
  ├─→ CHIPDeviceManager::Init()
  │    └─ Matter 初始化与 BLE 广告
  │
  ├─→ local_output_init()
  │    └─ CPU1 灯控系统启动
  │
  ├─→ stack_monitor_start()
  │    └─ 后台栈使用监测
  │
  └─→ PlatformMgr().ScheduleWork(init_server)
       └─ 启动 Matter 应用服务器
           ├─ mDNS 服务发布
           ├─ Fabric 表恢复
           └─ 准备接收命令
```

### 6.2 WiFi 与 IP 状态转迁

```
                    ┌─────────► WiFi_Connecting
                    │
device_boot
    │
    ├─→ WiFi_Init
    │     │
    │     ├─→ Scan & Connect
    │     │
    │     └─→ WiFi_Connected ◄─────┐
    │                    │          │
    │              DHCP Request      │
    │                    │          │
    │         IP_EVENT_STA_GOT_IP ───┤
    │                    │          │
    │     ┌──────────────┼──────────┤
    │     │              │          │
    │  RTC_Init      UDP_Start   MQTT_Init
    │     │              │          │
    │  Geo Locate & SNTP Sync
    │     │              │          │
    │  Time Set          │          │
    │                    │          │
    ⓘ All Services Ready │          │
      (State: READY)     │          │
                         │          │
    ◄─────────────────────────────┘

离线降级:
    WiFi Lost (or IP Lost)
         ▼
    IP_EVENT_STA_LOST_IP
         ▼
    MQTT_Disconnect
    UDP_Offline (local only)
    RTC_Suspend
         ▼
    BLE-Only Mode (still responsive)
         ▼
    WiFi Reconnect ──→ (回到 IP_EVENT_STA_GOT_IP)
```

### 6.3 可用性矩阵

| 功能 | 无网络 | 仅 WiFi | 完全联网 |
|------|--------|--------|----------|
| **本地控制** | ✅ BLE + 按键 | ✅ 完整 | ✅ 完整 |
| **定时任务** | ✅ 有效 | ✅ 有效 | ✅ 有效 |
| **灯光动画** | ✅ 有效 | ✅ 有效 | ✅ 有效 |
| **时间同步** | ❌ 无法获更新 | ✅ SNTP 就绪 | ✅ 活跃 |
| **云端 MQTT** | ❌ 无法连接 | ✅ 连接中 | ✅ 活跃 |
| **Matter 协议** |  ❌ 线下 | ✅ 线上 | ✅ 线上 |
| **UDP 接收** | ❌ 无 | ✅ 有效 | ✅ 有效 |

---

## 7. 关键设计决策

### 7.1 为什么选择双核隔离？

**问题**：单核系统中，网络中断会阻塞本地业务，导致灯光控制卡顿。

**方案**：
- CPU0 处理所有网络 IO（可能阻塞、延迟）
- CPU1 处理本地业务（实时性高，网络隔离）
- 通过 IPC 异步消息队列协作

**效果**：
- ✅ 网络并发高、本地响应快（≤ 16ms）
- ✅ 网络崩溃不影响灯具本身
- ✅ 易于扩展新协议（只在 CPU0 添加）

### 7.2 为什么用 StateManager 而非协议特定的状态？

**问题**：每个协议维护自己的状态 → 数据不一致、冲突

**方案**：
全系统使用单一真值来源 (Single Source of Truth)
```
MQTT state v=100
    ↓
StateManager v=101 ← Matter state v=100 → 冲突检测 → 使用更新版本
    ↓
UDP state v=101
```

**效果**：
- ✅ 保证多协议同步
- ✅ 版本号机制自动防重复
- ✅ 时间戳可追溯

### 7.3 为什么在 IP 就绪时启动 RTC/MQTT/UDP？

**问题**：早期启动可能导致连接卡住或资源竞争

**方案**：
IP_EVENT_STA_GOT_IP 事件触发三大网络服务
```
if (got_ip) {
    app_rtc_init();              // 时间同步是首先
    local_output_start_network_services();  // UDP
    mqtt_agent_init();           // MQTT
}
```

**效果**：
- ✅ 有网才启动（不浪费资源）
- ✅ 三者启动顺序一致
- ✅ SNTP 校准系统时间供后续使用

---

## 8. 扩展性与未来规划

### 8.1 添加新协议的步骤

1. **在 CPU0 新建协议驱动**
   ```
   components/myprotocol/
   ├─ include/myprotocol.h
   ├─ src/myprotocol.c
   └─ CMakeLists.txt
   ```

2. **注册命令处理器**
   ```c
   protocol_set_command_handler(PROTOCOL_ID_MYPROTO, myproto_handle_cmd);
   ```

3. **监听状态更新事件**
   ```c
   protocol_dispatcher_register_listener(myproto_on_state_changed);
   ```

4. **编码与发送状态**
   ```c
   void myproto_on_state_changed(device_state_t* state) {
       encode_my_format(state);
       send_to_peer();
   }
   ```

### 8.2 添加新硬件驱动的步骤

1. **CPU1 添加驱动**
   ```
   main/drivers/mydevice/
   ├─ mydevice.h
   ├─ mydevice.c
   └─ integration to dev_lamp.c
   ```

2. **集成到灯效系统**
   ```c
   void dev_lamp_apply_state(device_state_t* state) {
       // 既有逻辑...
       
       // 新驱动
       mydevice_set_output(state->color, state->matter_level);
   }
   ```

3. **在 IPC 消息中反馈**
   ```c
   if (hardware_error)
       ipc_send_error(CPU0_ERROR_MYDEVICE_FAIL);
   ```

---

## 9. 性能指标

| 指标 | 目标 | 当前状态 | 备注 |
|------|------|---------|------|
| **本地控制延迟** | ≤ 16 ms | ✅ 11-14 ms | 16ms ≈ 60fps |
| **按键响应时间** | ≤ 100 ms | ✅ 50-80 ms | 含消抖 |
| **WiFi 重连时间** | ≤ 3s | ✅ 1.5-2.5s | 正常场景 |
| **Matter 命令延迟** | ≤ 500 ms | ✅ 200-400 ms | 局网 |
| **MQTT 消息延迟** | ≤ 2s | ⚠️ 1-2s | 取决于网络 |
| **RTC 时间精度** | ±1s/hour | ✅ ±100ms | SNTP 校准后 |
| **内存使用** | < 50% | ✅ 28-32% | 稳定 |
| **栈深度最大** | < 90% | 🟡 68% | IPC 需优化 |
| **无网工作时间** | 无限制 | ✅ 无限制 | BLE mode |

---

## 10. 已知限制与改进计划

### 10.1 当前限制

| 限制 | 影响 | 优先级 | 计划 |
|------|------|--------|------|
| **IPC 栈压力** | ipc0/ipc1 <512B | 🔴 高 | 增加栈大小到 8KB |
| **MQTT TLS 证书** | 连接需验证 | 🟡 中 | 更新 CA 证书/支持自签 |
| **时区固定** | 无自动夏令时 | 🟢 低 | POSIX TZ 规则已支持 |
| **集群属性读权限** | Matter err=501 | 🟢 低 | 正常处理，无需修复 |

### 10.2 未来规划 (2026-06)

- [ ] 云端 OTA 固件更新 (Matter OTA Requestor)
- [ ] 多 Fabric 跨域同步优化
- [ ] 本地存储加密 (NVS encryption)
- [ ] 蓝牙协议链路再启用
- [ ] 故障自愈机制（自动重启崩溃模块）
- [ ] 能效监测与优化

---

## 附录：关键代码位置

| 功能 | 文件位置 |
|------|---------|
| **主入口** | `main/main.cpp` - `app_main()` |
| **状态管理** | `components/framework/state_manager/src/state_manager.c` |
| **IPC 通信** | `components/framework/ipc_manager/src/ipc_manager.c` |
| **协议分发** | `components/framework/protocol_dispatcher/src/protocol_dispatcher.c` |
| **RTC 时区同步** | `main/app/app_rtc.c` + `components/network/sync_time/` |
| **Matter 回调** | `main/DeviceCallbacks.cpp` |
| **本地灯控** | `main/app/local_manager.c` + `components/app/local_output/src/local_output.c` |
| **MQTT 代理** | `components/network/mqtt_agent/src/mqtt_agent.c` |
| **UDP 接收** | `components/network/cmd_wifi/ambient_receiver.c` |

---

**下一步**：阅读 [BUILD.md](../development/BUILD.md) 了解编译与部署流程。
