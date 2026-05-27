# ESP32S3 智能灯具 - 快速参考手册

## 关键概念速览

### 核心三层架构

```
┌────────────────────────────────────────┐
│     应用逻辑层                          │
│  state_manager (状态管理中心)          │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│     同步层                              │
│  ipc_manager (核间通信)                │
│  protocol_dispatcher (协议分发)        │
└────────────────┬───────────────────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
CPU0 网络核                CPU1 业务核
├─ MQTT                  ├─ Input系统
├─ Matter                ├─ Output系统
├─ UDP                   ├─ Scheduler
└─ BLE                   └─ Logic
```

---

## 状态管理数据模型

```c
device_state_t {
    // 灯光参数
    bool power_on;           // 开/关
    uint8_t brightness;      // 亮度 0-100%
    uint16_t color_temp;     // 色温 2700-6500K
    uint8_t mode;            // 模式(normal/breathing/等)
    
    // 版本控制(防环路核心!)
    uint32_t version;        // ⭐ 每次变化递增
    uint64_t timestamp;      // ⭐ 变化时刻(ms)
    uint8_t last_source;     // ⭐ 最后修改者(0=本地,1=MQTT,...)
}
```

**关键规则**：
- 任何状态变化 → `version++` (防重复)
- 多协议同时下发 → 比较 `timestamp` 决定优胜者
- 消息来自同源 → 检查 `last_source` 防止回环

---

## IPC消息类型

| 消息类型 | 发送方 | 接收方 | 用途 |
|---------|--------|--------|------|
| STATE_UPDATE | CPU1✓ CPU0✓ | 对方 | 状态变化 |
| CONTROL_CMD | CPU0 | CPU1 | 云端控制命令 |
| NETWORK_STATUS | CPU0 | CPU1 | 网络状态通知 |
| PROTOCOL_EVENT | CPU0 | CPU1 | 协议事件(如Matter事件) |
| ERROR | 双向 | 对方 | 错误上报 |

**发送示例**：
```c
device_state_t new_state = {..., .version = 101, .timestamp = now_ms};
ipc_message_t msg = {
    .type = IPC_MSG_STATE_UPDATE,
    .priority = 2,
};
ipc_serialize_state(&new_state, msg.payload, &msg.payload_len);
ipc_send_to_cpu0(&msg);  // 或 ipc_send_to_cpu1(&msg)
```

---

## 两核任务分配表

### CPU0 (网络核) - 优先级参考

| 任务名 | 优先级 | 核心堆栈 | 职责 |
|--------|--------|---------|------|
| network_manager_task | 15 | 4KB | WiFi扫描/连接、IP检查、心跳监控 |
| mqtt_task | 10 | 8KB | MQTT连接、消息订阅/发布 |
| ble_task | 9 | 8KB | BLE广播、GATT服务、连接管理 |
| matter_task | 8 | 8KB | Matter Stack、Cluster处理 |
| udp_task | 7 | 6KB | UDP绑定、广播收发 |

**CPU0硬实时要求**：保持网络连接活跃，心跳检测

### CPU1 (业务核) - 优先级参考

| 任务名 | 优先级 | 核心堆栈 | 职责 |
|--------|--------|---------|------|
| local_manager_task | 10 | 8KB | 输入处理、定时器、输出执行 |
| input_system_scan | 11 | 4KB | 按键/传感器扫描(可选单独任务) |
| output_executor | 9 | 4KB | LED/PWM驱动(可选单独任务) |
| animation_engine | 8 | 6KB | 动画播放引擎 |

**CPU1软实时要求**：响应性好，16ms内响应输入

---

## 协议快速参考

# 快速参考手册

> **用途**：日常开发时的快速查询与故障排查  
> **更新日期**：2026-04-17  
> **分级难度**：⭐ 初级 | ⭐⭐ 中级 | ⭐⭐⭐ 高级

---

## 🚀 10 秒启动 (快速开始)

```bash
# 1. 进入项目目录
cd /home/ats/standard_code/Aputure_IP_Project

# 2. 一键编译、烧录、监测
idf.py flash monitor

# 3. 等待启动完成（~2.5 秒）
# 日志出现 "Server initialization complete" 即成功

# 4. 退出监测
Ctrl+]
```

---

## 🔧 常用命令速查

### 编译相关

```bash
# 完整编译
idf.py build

# 加速编译 (并行)
idf.py -j$(nproc) build

# 清理后重新编译
idf.py fullclean && idf.py build

# 仅验证 MQTT 组件相关改动
idf.py build
# 或使用 CMake 目标
cmake --build build --target esp-idf/mqtt_agent/libmqtt_agent.a -j$(nproc)
```

### 烧录相关

```bash
# 自动检测端口并烧录
idf.py flash

# 指定端口
idf.py -p /dev/ttyACM0 flash

# 烧录 + 联网 + 监测 (一条命令)
idf.py flash monitor

# 擦除全部 FLASH
idf.py erase-flash
```

### 监测相关

```bash
# 基础监测
idf.py monitor

# 带时间戳
idf.py monitor --timestamps

# 保存日志到文件
idf.py monitor | tee $(date +%s).log

# 指定波特率
idf.py -b 230400 monitor
```

### 配置相关

```bash
# 打开图形菜单配置
idf.py menuconfig

# 保存并自动重新编译
# 在菜单中按 S 保存，然后 Q 退出

# 查看当前配置
grep "CONFIG_" sdkconfig | head -20
```

---

## 📋 关键配置项

**位置**：`sdkconfig` 或 `sdkconfig.defaults` 或 `idf.py menuconfig`

```ini
# ========== 串口配置 ==========
CONFIG_ESP_CONSOLE_UART_NUM=1           # 使用 UART1
CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y   # 或使用 USB JTAG

# ========== FreeRTOS ==========
CONFIG_FREERTOS_HZ=1000                 # 时钟频率 1ms

# ========== 日志输出 ==========
CONFIG_LOG_DEFAULT_LEVEL_INFO=y         # 默认 INFO 等级
CONFIG_LOG_COLORS=y                     # 彩色输出

# ========== Wi-Fi ==========
CONFIG_LWIP_DHCP_RESTORE_STATE=y       # DHCP 状态持久化
CONFIG_AMBIENT_IP_CHECK_INTERVAL_MS=5000  # IP有效性轮询间隔(ms)

# ========== 本地输出 ==========
CONFIG_LOCAL_OUTPUT_ENABLE_BLUETOOTH_APP=n  # 蓝牙 (当前禁用)

# ========== 热保护 (Thermal Protection) ==========
CONFIG_THERMAL_OVER_TEMP_THRESHOLD_C=85      # 过温进入阈值(摄氏度)
CONFIG_THERMAL_RECOVER_TEMP_THRESHOLD_C=78   # 过温恢复阈值(摄氏度)
CONFIG_THERMAL_DERATE_POWER_LIMIT_PCT=60     # 过温时功率上限(%)
CONFIG_THERMAL_NORMAL_POWER_LIMIT_PCT=100    # 正常时功率上限(%)

# ========== 构建 ==========
CONFIG_COMPILER_OPTIMIZATION_SIZE=n     # 优化为速度
CONFIG_COMPILER_OPTIMIZATION_PERF=y
```

---

## 🌡️ 热保护调参速查

**菜单路径**：`idf.py menuconfig` → `Project Configuration` → `Thermal Protection`

| 参数 | 默认值 | 推荐区间 | 说明 |
|------|--------|----------|------|
| `THERMAL_OVER_TEMP_THRESHOLD_C` | 85 | 80-95 | 超过该温度进入过温保护 |
| `THERMAL_RECOVER_TEMP_THRESHOLD_C` | 78 | 70-90 | 低于该温度退出过温保护 |
| `THERMAL_DERATE_POWER_LIMIT_PCT` | 60 | 40-80 | 过温状态下灯具功率上限 |
| `THERMAL_NORMAL_POWER_LIMIT_PCT` | 100 | 90-100 | 正常状态功率上限 |

**调参约束**：
- `RECOVER_TEMP` 必须小于 `OVER_TEMP`，建议至少保留 5°C 滞回
- `DERATE_POWER_LIMIT_PCT` 必须小于 `NORMAL_POWER_LIMIT_PCT`
- 高温环境建议优先降低 `DERATE_POWER_LIMIT_PCT`，再调整阈值

**推荐调参步骤**：
1. 保持默认值运行，记录 10 分钟稳定温度
2. 若频繁进入/退出过温，增大滞回（提高过温阈值或降低恢复阈值）
3. 若温度持续高于目标，降低 `DERATE_POWER_LIMIT_PCT`（如 60 → 50）
4. 每次改动后执行 `idf.py reconfigure && idf.py build`
5. 烧录后做 20-30 分钟恒定负载回归测试

**验收日志检查点**：
```bash
# 查找温度与过温状态变更
grep -Ei "temp|over_temp|thermal" monitor.log

# 查找功率限制下发
grep -Ei "power_limit|derate" monitor.log
```

**预期现象**：
- 温度上升到过温阈值后，日志出现 over_temp=true，且 power_limit 下调
- 温度降到恢复阈值以下后，日志出现 over_temp=false，且 power_limit 恢复

---

## 📐 启动日志里程碑

找不到某个日志？看这个对应表：

| 里程碑 | 日志内容 | 时间 | 备注 |
|-------|---------|------|------|
| 系统启动 | `app_init: Project name: aputure_ip_project` | 389ms | ✅ 固件检查成功 |
| 日志系统 | `AputureIP: logger initialized` | 409ms | ✅ 日志系统就绪 |
| 灯效初始化 | `dev_lamp: 1ms软件定时器初始化完成` | 529ms | ✅ PWM 驱动配置 |
| 栈监控启动 | `stack_monitor: stack snapshot begin` | 555ms | ✅ 任务监测活跃 |
| Matter 启动 | `CHIPoBLE advertising started` | 1128ms | ✅ BLE 广告发送 |
| WiFi 连接 | `wifi:connected with AP-IOT` | 1222ms | ✅ 已关联 AP |
| IP 获取 | `got ip: 192.168.9.105` | 2260ms | ✅ DHCP 成功 |
| **⭐ RTC 启动** | `network time/timezone sync task started` | 2248ms | ✅ **新增** |
| 地理定位 | `GEO_LOCATION: 地理位置查询成功` | 4068ms | ✅ 位置已确定 |
| 时间同步 | `SNTP_TIME: 时间同步完成` | 4965ms | ✅ 系统时间已校准 |
| Matter 就绪 | `Server initialization complete` | 2530ms | ✅ 所有服务就绪 |

---

## 🐛 故障排查指南

### 问题 1: 编译失败

```
错误: undefined reference to '_Z12app_rtc_initv'
┗━━ 原因：C/C++ 符号名改编冲突
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✅ 解决1：检查 app_rtc.h 是否有 extern "C"
✅ 解决2：清理并重新编译
    idf.py fullclean && idf.py build
```

```
错误: undefined reference to 'mqtt_agent_init'
┗━━ 原因：main/CMakeLists.txt 未包含 mqtt_agent 组件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✅ 解决：在 main/CMakeLists.txt 的 REQUIRES 中添加 mqtt_agent
```

### 问题 2: 无网络连接

```
症状：日志显示 WiFi 搜索但未连接
    W (1134) wifi:Haven't to connect to a suitable AP now!
┗━━ 原因：SSID/密码配置错误 或 AP 距离太远
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✅ 解决1：检查 CONFIG_AMBIENT_WIFI_SSID 和 pwd
    grep "AMBIENT_WIFI" components/network/cmd_wifi/include/ambient_config.h
  
✅ 解决2：更改配置
    编辑 ambient_config.h，改为正确的 SSID/密码

✅ 解决3：检查 IP 轮询周期是否过长
    grep "AMBIENT_IP_CHECK_INTERVAL_MS" sdkconfig sdkconfig.defaults
    # 建议 1000-5000ms，网络抖动场景可适当缩短
  
✅ 解决3：重新编译烧录
    idf.py fullclean && idf.py flash monitor
```

### 问题 3: MQTT 连接失败

```
症状：反复出现
    E (2749) esp-tls-mbedtls: Failed to verify peer certificate!
    E (2752) mqtt_client: Error transport connect
┗━━ 原因：TLS 证书验证失败
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✅ 解决1：临时禁用证书验证 (仅测试)
    编辑 components/network/mqtt_agent/src/mqtt_agent.c
    mqtt_cfg.crt_bundle_attach = NULL;  // 暂时禁用
  
✅ 解决2：更新 CA 证书
    openssl s_client -connect broker.emqx.io:8883 -showcerts
    复制证书并更新 components/network/mqtt_agent/certs/emq_root_ca.pem
  
✅ 解决3：检查网络
    ping broker.emqx.io
    检查是否可以解析 DNS
```

### 问题 4: RTC 时间同步失败

```
症状：地理定位失败或时间未更新
    W (3248) TIMEZONE_SYNC: 地理位置获取失败，使用默认时区
    W (4965) SNTP_TIME: 时间同步失败
┗━━ 原因：网络不通 或 API 服务不可用
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✅ 解决1：检查网络连接
    看日志中是否有 "got ip: 192.168.x.x"
  
✅ 解决2：检查地理定位 API
    在电脑上测试：
    curl http://ip-api.com/json/
  
✅ 解决3：检查 SNTP 服务器
    ping asia.pool.ntp.org
  
✅ 解决4：查看详细日志
    idf.py monitor 中搜索 "TIMEZONE_SYNC" 或 "GEO_LOCATION"
```

### 问题 5: 栈溢出警告

```
症状：栈监控告警
    W (560) stack_monitor: LOW STACK task=ipc0 free_min=456B (<512B)
┗━━ 原因：IPC 任务栈初始化过小
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✅ 解决 (需要修改代码)：
    编辑 components/framework/ipc_manager/CMakeLists.txt
    找到 xTaskCreate 调用，修改栈大小：
    - 原: xTaskCreate(..., 4096, ...)
    + 新: xTaskCreate(..., 8192, ...)
  
    重新编译烧录
    idf.py fullclean && idf.py flash monitor
```

### 问题 6: RS485 从机离线

```
症状：启动日志显示
    I (3594) app_rs485_master: 从机未连接
┗━━ 原因：RS485 线缆连接不稳定 或 从机无电源
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✅ 解决：
    1. 检查 RS485 A、B 线是否接对
    2. 检查从机电源是否打开
    3. 检查总线是否被其他设备占用
    4. 用万用表测量 A-B 引脚电压（应为 2-3V）
  
    如仍不行，可禁用 RS485 进行其他测试：
    编辑 main/app/local_manager.c
    注释掉 rs485_master 相关初始化
```

---

## 🧩 核心代码片段

### 获取当前系统时间

```c
#include <time.h>

time_t now = time(NULL);
struct tm* tm_info = localtime(&now);

printf("Current time: %d-%02d-%02d %02d:%02d:%02d\n",
        tm_info->tm_year + 1900,
        tm_info->tm_mon + 1,
        tm_info->tm_mday,
        tm_info->tm_hour,
        tm_info->tm_min,
        tm_info->tm_sec);

// 输出: Current time: 2026-04-17 14:29:03
```

### 手动更改灯具状态

```c
#include "state_manager.h"

device_state_t state = {0};
state_manager_get_state(&state);

// 改变亮度
state.matter_level = 200;        // 0-254
state.power_on = true;            // 开灯

// 改变颜色 (HSI 模式)
state.color.mode = LIGHT_MODE_HSI;
state.color.value.hsi.hue = 120;  // 绿色
state.color.value.hsi.sat = 100;  // 饱和度
state.color.value.hsi.lightness = 50;

// 更新
state_manager_set_state(&state);

// 其他协议会自动收到更新事件
```

### 订阅状态变化

```c
#include "state_manager.h"

// 定义回调
void my_state_changed_callback(const device_state_t* new_state) {
        ESP_LOGI(TAG, "State changed: level=%d, power=%d",
                         new_state->matter_level, new_state->power_on);
}

// 注册回调
state_manager_register_listener(my_state_changed_callback);

// 从此之后每次状态变化都会自动调用此函数
```

### 发送 IPC 消息

```c
#include "ipc_queue.h"

// 定义消息
ipc_message_t msg = {
        .type = IPC_TYPE_SET_LEVEL,
        .priority = 10,
        .payload = (void*)(intptr_t)200,  // 亮度值
        .payload_len = 1
};

// 发送给 CPU1
ipc_send(IPC_QUEUE_CPU1, &msg);

// 不需要等待回复，非阻塞
```

---

## 📊 日志级别控制

### MQTT

```c
# 编译时修改
light/control      // 订阅: 接收云平台控制
# 进入 Component config -> Log output -> Default log verbosity
light/status       // 发布: 上报状态变化
    "mode": "normal",
    "version": 101,
    "timestamp": 1712572335000
}

// 关键参数
- Broker: mqtt://broker.aliyun.com:1883
- QoS: 1 (至少一次)
- Keep-Alive: 60秒
- 重连策略: 指数退避, 最大30秒间隔
```

### BLE

```c
// 关键Service/Characteristic
Service UUID: FFE0 (自定义)
├─ FFE1 (Read)   : 设备状态
├─ FFE2 (Write)  : 控制命令
└─ FFE3 (Notify) : 状态推送

// 典型命令格式 (二进制)
Byte 0: 命令类型
    0x01 = 开/关
    0x02 = 设置亮度
    0x03 = 设置色温
    0x04 = 设置模式
    ...
Byte 1-N: 参数

// 示例 (打开灯，亮度80%)
0x02 0x50 (亮度80)
```

### Matter

```c
// 适用的Cluster
OnOff (0x0006)
├─ Attribute: on_off (bool)
├─ Command: On, Off, Toggle
└─ Event: OnOff

LevelControl (0x0008)
├─ Attribute: current_level (0-254)
└─ Command: MoveToLevel

ColorControl (0x0300)
├─ Attribute: color_x, color_y
└─ Command: MoveToColorTemp

// Matter指令示例
OnOff::SetAttribute("on_off", true);
LevelControl::MoveToLevel(level=204, transition_time=0);
```

### UDP

```c
// 端口: 5500
// 广播地址: 255.255.255.255

// 消息格式 (Binary)
Frame Header:
├─ Magic: 0xABCD (2B)
├─ Version: 0x01 (1B)
├─ Type: 见下表 (1B)
├─ Payload Length: (2B)
└─ Payload: 可变长

消息类型:
0x01 = STATE_BROADCAST   (灯→局域网: 状态同步)
0x02 = CMD_BROADCAST     (APP→灯: 控制命令)
0x03 = STATE_QUERY       (APP→灯: 查询当前状态)
0x04 = STATE_RESPONSE    (灯→APP: 状态回应)
```

---

## 网络状态转换快速查表

```
系统启动
  ↓
[无WiFi配置] ─────→ BLE-Only模式 ⟷ 等待配网
[有WiFi配置]
  ↓
WiFi连接
  ├─ 成功 ⟷ 检查IP有效性 ⟷ [IP有效]
  │        │                    ↓
  │        │              启动所有协议 → 完全就绪
    │        │              (MQTT/Matter/UDP/BLE)
  │        │                    ↑
  │        │         [心跳检查] 正常
  │        │
  │        └─[超时] ─────→ BLE-Only模式
  │              或无IP
  └─ 失败5次 ──→ BLE-Only模式

BLE-Only模式:
├─ 启动BLE广播 ✓
├─ 关闭MQTT等协议 ✓
├─ CPU1继续工作 ✓
├─ 定期扫描WiFi (30秒x次)
└─ WiFi恢复 → 返回正常流程
```

---

## 版本号与防环路机制

### 问题场景

```
MQTT发送: 亮度80 (v=100)
    ↓
StateManager更新 (v=101)
    ↓
Matter检测到变化
    ↓
Matter发送事件: 亮度80 (v=?)  ← 这里容易环路!
    ↓
再次更新StateManager?
    ↓
MQTT再次发送? ← 无限循环!
```

### 解决方案

```c
// 1️⃣ 版本号自动递增
void state_manager_set_state(...) {
    new_state.version++;  // 101 → 102
    new_state.timestamp = now_ms;
}

// 2️⃣ 记录消息来源
new_state.last_source = PROTOCOL_MQTT;  // 记录谁修改的

// 3️⃣ 分发时跳过来源
protocol_dispatcher_publish_state(&state, PROTOCOL_MQTT);
// ↑ 参数2 = 跳过MQTT，不会再发一遍

// 4️⃣ 接收时去重
if (new_version <= cached_version) {
    return;  // 丢弃旧消息
}

// 5️⃣ 时间戳判断
if (new_timestamp < last_timestamp) {
    return;  // 丢弃更旧的消息
}
```

---

## 常见操作代码片段

### 更新灯光亮度

```c
// 本地按键调节亮度
void handle_brightness_increase(void) {
    device_state_t state = state_manager_get_state();
    if (state.brightness < 100) {
        state.brightness += 10;
        state_manager_set_state(&state, PROTOCOL_LOCAL);
        // ↑ set_state自动处理:
        //   ✓ version++
        //   ✓ timestamp更新
        //   ✓ IPC发送到CPU0
        //   ✓ 触发回调函数
        //   ✓ protocol_dispatcher分发
    }
}

// MQTT接收云端命令
void mqtt_on_brightness_command(uint8_t brightness) {
    device_state_t state = state_manager_get_state();
    state.brightness = brightness;
    state_manager_set_state(&state, PROTOCOL_MQTT);
    // set_state自动跳过MQTT重复发布
}
```

### 监听状态变化

```c
// 注册回调
void on_state_changed(const device_state_t *old, const device_state_t *new) {
    if (old->brightness != new->brightness) {
        // 亮度变化
        pwm_set_brightness(new->brightness);
    }
    
    if (old->power_on != new->power_on) {
        // 开关变化
        if (new->power_on) {
            led_on();
        } else {
            led_off();
        }
    }
}

state_manager_on_change(on_state_changed);
```

### 定时任务

```c
// 注册每天6:00开灯
scheduler_add_cron_task(
    "light_on_morning",
    "0 6 * * *",  // Cron表达式: 0点 分 小时 日 月 周
    on_morning_light_callback
);

void on_morning_light_callback(void *arg) {
    device_state_t state = state_manager_get_state();
    state.power_on = true;
    state.brightness = 100;
    state_manager_set_state(&state, PROTOCOL_LOCAL);  // source=LOCAL
}

// 注册倒计时关灯
scheduler_add_countdown_task(
    "sleep_timer",
    30 * 60 * 1000,  // 30分钟(毫秒)
    on_sleep_timer_callback
);

void on_sleep_timer_callback(void *arg) {
    device_state_t state = state_manager_get_state();
    state.power_on = false;
    state_manager_set_state(&state, PROTOCOL_LOCAL);
}
```

---

## 故障快速诊断

### 症状→原因→解决

```
症状: 设备收到MQTT命令但没反应

原因排查路径:
  1. MQTT是否连接? 
     → ESP_LOGI检查mqtt_client != NULL
  2. 消息是否订阅到?
     → 检查log中 "subscribe to light/control"
  3. CPU0是否接收到?
     → 在mqtt_handler中打log
  4. IPC消息是否发给CPU1?
     → 检查 ipc_send_to_cpu1() 返回值
  5. CPU1是否执行了?
     → 在handle_ipc_message中打log
  6. 输出系统是否工作?
     → 检查 pwm_set_brightness() 返回值
  7. GPIO是否配置正确?
     → 用示波器查看GPIO电平
```

### 常用日志关键词搜索

```
// CPU0网络健康度
grep "mqtt_client connected" logs    // MQTT连接
grep "matter_joined" logs            // Matter加入
grep "udp_listening on" logs         // UDP监听
grep "ble_advertise_started" logs    // BLE广播

// CPU1健康度
grep "input_event" logs              // 按键事件
grep "pwm_brightness" logs           // LED响应
grep "scheduler_tick" logs           // 定时器心跳

// 同步诊断
grep "version mismatch" logs         // 版本号冲突
grep "loop detected" logs            // 环路检测
grep "drop duplicated" logs          // 去重发生
```

---

## 对标三方方案对比

| 功能维度 | SmartLight | 小米 | LIFX | Philips Hue |
|---------|-----------|------|------|-------------|
| **本地控制** | ✓ 按键 | ✓ | ✗ | ○ 受限 |
| **离线工作** | ✓ BLE-Only | ○ | ✗ | ○ 受限 |
| **多协议** | ✓ 5种 | ○ | ✓ | ✓ |
| **自建布署** | ✓ 开源 | ✗ | ✗ | ○ 付费中心器 |
| **功耗** | ✓ 优化 | ○ | ✗ 耗电 | ○ |
| **成本** | ✓ 低 | ✓ | ✗ 高 | ✗ 高 |
| **隐私** | ✓ 本地 | ✗ | ✗ | ○ |

**核心竞争力**：本地+云双轨、完全开源、极简双核设计

