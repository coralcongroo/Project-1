# 开发者指南

> **用途**：指导新开发者快速上手项目，理解开发流程与编码规范  
> **更新日期**：2026-04-17  
> **目标受众**：新入库开发者、贡献者

---

## 📖 快速上手 (15 分钟)

### 1. 环境准备

```bash
# 1. 安装 ESP-IDF v5.4+
# 参考官网：https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/get-started/index.html

# 2. 克隆项目
git clone <repo_url.git> Aputure_IP_Project
cd Aputure_IP_Project

# 3. 初始化 IDF 环境（每次新终端）
. $IDF_PATH/export.sh

# 4. 构建项目
idf.py build
```

### 2. 烧录与测试

```bash
# 一键烧录 + 监测
idf.py flash monitor

# 预期日志序列（2.5 秒内完成）：
# [✓] System init → WiFi connect → IP acquired → RTC sync → Matter ready
```

### 3. 查看代码结构

```bash
# 熟悉核心文件
tree -L 2 main/
tree -L 2 components/

# 关键文件位置：
# 📌 入口点:        main/main.cpp::app_main()
# 📌 RTC 时间同步:  main/app/app_rtc.c
# 📌 Matter 集成:    main/DeviceCallbacks.cpp
# 📌 IPC 消息队列:  components/framework/ipc_manager/
# 📌 状态管理:      components/framework/state_manager/
# 📌 协议分发:      components/framework/protocol_dispatcher/
# 📌 本地灯控:      components/app/local_output/ + main/app/local_manager.c
```

---

## 🎯 核心概念理解

### 架构层级

```
应用层 (Application)
  ↓
状态管理层 (StateManager) - 单一真值源
  ↓
协议分发层 (ProtocolDispatcher) - 路由 + 防环路
  ↓
核间通信层 (IPC Manager) - 消息队列
  ↓ ↓
CPU0 (网络)      CPU1 (本地业务)
├─ Matter        ├─ LED/PWM
├─ MQTT          ├─ RS485
├─ UDP           ├─ 按键输入
├─ BLE           └─ 定时任务
└─ SNTP RTC      
```

### 数据流示例：云端 → 本地

```
云端 MQTT Broker
  ↓ publish "iot/device/{mac}/down": {"level": 200}
  ↓
MQTT Agent (CPU0) - 接收
  ↓ ipc_send()
  ↓
IPC Queue - 传输
  ↓ wake CPU1
  ↓
CPU1 Task - 接收 IPC 消息
  ↓ state_manager_set_state()
  ↓
StateManager - 更新状态 (version++)
  ↓ notify listeners
  ↓
Local Output Driver
  ↓ set LED brightness = 200
  ↓
LED 亮度立即改变 ✅

& 同时 (不阻塞)
CPU0 StateManager listener
  ↓ publish "report/data": {"level": 200, "version": 123}
  ↓
MQTT Broker - 状态上报完成
```

### IP-Ready-Gate 启动时序

```
Boot
  ↓ Wait for WiFi
  ↓ (1-2 秒)
  ↓ WiFi Connected + DHCP
  ↓ IP_EVENT_STA_GOT_IP 触发
  ├─→ app_rtc_init() ──→ 地理定位 + SNTP ──→ 系统时间同步 ✅
  │                     (~2 秒)
  ├─→ local_output_start_network_services() ──→ UDP/Matter 初始化 ✅
  │                                            (~0.5 秒)
  └─→ mqtt_agent_init() ──→ MQTT 连接 ⚠️ (TLS 证书问题)
     (~1 秒)

总耗时: ~3.5 秒 (从 IP 到所有服务就绪)
```

---

## 🛠️ 常见开发任务

### 任务 1: 新增本地灯效

**文件位置**：`components/lighting/light_effect_pixel/`（像素光效）或 `main/light/`（本地灯控编排）

**步骤**：

```c
// 1. 在 led_effects.h 中定义新灯效 ID
#define LED_EFFECT_RAINBOW 8  // 新增彩虹灯效

// 2. 实现灯效方程
void led_effect_rainbow(led_context_t* ctx) {
    // 计算 HSL 颜色
    for (int i = 0; i < 60; i++) {
        float hue = (i + ctx->tick) % 60 * 6.0;  // 0-360 度
        set_led_hsl(i, hue, 100, 50);
    }
    ctx->tick = (ctx->tick + 1) % 60;
}

// 3. 在灯效表中注册
const led_effect_fn effects[] = {
    led_effect_solid,
    led_effect_pulse,
    // ...
    led_effect_rainbow,  // 新增
};

// 4. 验证
idf.py build
# 查看编译日志中 LED_EFFECT_RAINBOW 是否被识别
```

### 任务 2: 新增 MQTT 主题监听

**文件位置**：`components/network/mqtt_agent/src/mqtt_agent.c`

**步骤**：

```c
// 1. 定义主题
#define MQTT_TOPIC_CUSTOM_CMD "iot/device/+/custom_cmd"

// 2. 在 mqtt_event_handler 中处理
case MQTT_EVENT_DATA:
    if (strcmp(event->topic, MQTT_TOPIC_CUSTOM_CMD) == 0) {
        handle_custom_command(event->data, event->data_len);
    }
    break;

// 3. 实现处理函数
void handle_custom_command(const char* data, int len) {
    cJSON* json = cJSON_ParseWithLength(data, len);
    if (!json) return;
    
    // 解析并执行命令
    // ...
    
    cJSON_Delete(json);
}

// 4. 测试
idf.py build && idf.py flash monitor
# 使用 MQTT 客户端工具发送测试消息
```

### 任务 3: 修改 Matter 集群属性

**文件位置**：`main/DeviceCallbacks.cpp`

**步骤**：

```cpp
// 1. 在 ZCL_ATTRIBUTE_DATA_TYPE_INT8U 表中添加新属性
// 例如：添加"灯效模式"属性
ZCL_ATTRIBUTE(0x4008, ZCL_UINT8_ATTRIBUTE_TYPE, R | W, effect_mode)

// 2. 在属性读取回调中处理
uint8_t effect_mode_callback(AttributeId attr) {
    device_state_t state;
    state_manager_get_state(&state);
    return state.led_effect;
}

// 3. 在属性写入回调中处理
void effect_mode_write_callback(AttributeId attr, uint8_t value) {
    device_state_t state;
    state_manager_get_state(&state);
    state.led_effect = value;
    state_manager_set_state(&state);
}

// 4. 测试
# 使用 Matter 控制器应用读写此属性
```

### 任务 4: 调试 RTC 时间同步

**文件位置**：`main/app/app_rtc.c`

**步骤**：

```c
// 1. 提升日志级别查看详细过程
esp_log_level_set("APP_RTC", ESP_LOG_DEBUG);
esp_log_level_set("TIMEZONE_SYNC", ESP_LOG_DEBUG);
esp_log_level_set("SNTP_TIME", ESP_LOG_DEBUG);

// 2. 手动测试地理定位 API
// 在电脑上运行
curl -s http://ip-api.com/json/ | jq .
# 确保可以返回地理位置信息

// 3. 监测 SNTP 同步过程
idf.py monitor | grep -E "(SNTP|TIMEZONE|GEO)"

// 4. 如无反应，检查从机代码
grep -n "geo_locate\|timezone_sync_create" main/app/app_rtc.c
# 确认是否正确调用
```

---

## 📋 编码规范

### C/C++ 混编规则

**Location**: `main/app/app_rtc.h`

```c
// ✅ 正确做法：用 extern "C" 包装 C 函数
extern "C" {
    void app_rtc_init(void);
    void rtc_thread_entry(void* arg);
}

// ❌ 错误做法：C 函数在 C++ 中未包装 →编译失败
// 产生 undefined reference '_Z12app_rtc_initv' 错误
```

### 宏定义规范

```c
// ✅ 使用配置宏替代硬编码
#define WIFI_SSID CONFIG_AMBIENT_WIFI_SSID
#define WIFI_PASSWORD CONFIG_AMBIENT_WIFI_PASSWORD

// ❌ 不要硬编码
// #define WIFI_SSID "AP-IOT"
```

### 日志记录规范

```c
// ✅ 推荐格式
ESP_LOGI(TAG, "Device state updated: level=%d, power=%d", 
         state.light_level, state.power_on);

// ⚠️ 避免过度日志
ESP_LOGD(TAG, "loop iteration %d", count);  // 仅在 DEBUG 级别
```

### 任务优先级规范

```c
// FreeRTOS 优先级：0 = 最低, 31 = 最高

#define PRIORITY_IDLE       tskIDLE_PRIORITY           // 0
#define PRIORITY_LOW        tskIDLE_PRIORITY + 1       // 1
#define PRIORITY_NORMAL     tskIDLE_PRIORITY + 5       // 5
#define PRIORITY_HIGH       tskIDLE_PRIORITY + 10      // 10
#define PRIORITY_CRITICAL   configMAX_PRIORITIES - 1   // 30

// ✅ 示例：灵敏响应任务使用高优先级
xTaskCreate(local_output_task, "local_out", 8192, NULL, 
            PRIORITY_HIGH, NULL);
```

---

## 🔍 代码审查清单

提交 PR 前，自检：

```
□ 编译无警告
  idf.py build 2>&1 | grep -i warning

□ 烧录成功
  idf.py flash 成功完成

□ 启动日志无异常
  日志中无 ERROR / FATAL / PANIC

□ 功能测试通过
  用户故事场景都验证过

□ C/C++ 混编无冲突
  所有 C 函数都有 extern "C" 保护

□ 硬编码值已配置化
  检查是否使用 CONFIG_* 宏

□ 栈使用合理
  不会触发 LOW STACK 告警

□ 无资源泄漏
  Task 创建后有清理、内存分配有释放

□ 日志输出充分
  关键路径都有 INFO 级别日志

□ 文档已更新
  修改 API 时更新对应 .md 文件
```

---

## 🚀 工作流程

### 日常开发流程

```
1. 创建特性分支
   git checkout -b feature/my-feature

2. 开发与测试
   idf.py build && idf.py flash monitor
   # 在终端中验证功能

3. 运行单元测试(如有)
   idf.py test

4. 代码自检
   # 使用上面的代码审查清单

5. 提交 Commit
   git add .
   git commit -m "feat: add RTC SNTP integration"

6. 推送 PR
   git push origin feature/my-feature
   # 在 GitHub 上创建 Pull Request

7. 等待代码审查通过
   # 至少 1 个 Approver 同意后合并

8. 合并到 main
   git merge --squash feature/my-feature
```

### 发布新版本

```
前置条件：
- 所有 PR 已合并
- 24+ 小时稳定性测试通过
- 无 🔴 高优先级 Issue 未解决

步骤：
1. 更新版本号
   编辑 main/CMakeLists.txt: PROJECT_VERSION
  编辑 docs/development/CHANGELOG.md

2. 标记版本
   git tag -a v1.2.0 -m "Release v1.2.0"

3. 构建产品固件
   idf.py build -D CMAKE_BUILD_TYPE=Release

4. 上传发布
   在 GitHub Releases 页面创建新版本
   附加编译产物
```

---

## 🧪 测试指南

### 单元测试

```bash
# 构建并运行单元测试（如存在）
idf.py build -t test
idf.py test

# 当前已有测试：
# tests/test_state_manager.c
# tests/test_ipc_message.c
# tests/test_protocol_dispatcher.c
```

### 集成测试

```bash
# 场景 1: 本地灯控响应
# 步骤: 通过 ipc_send() 改变灯的亮度并观察 LED

# 场景 2: MQTT 状态同步
# 步骤: 云端发送 MQTT 命令 → 本地灯做出反应 → 状态上报

# 场景 3: RTC 时间同步
# 步骤: 观察日志中地理定位和 SNTP 是否完成

# 场景 4: Matter 协议
# 步骤: 用 Matter 控制器发送属性读/写
```

### 性能测试

```bash
# 监控堆内存
esp_heap_trace_init_standalone(buf, buf_len);
esp_heap_trace_start(HEAP_TRACE_ALL);
// ... 运行代码 ...
esp_heap_trace_dump(stdout);

# 监控任务栈
# 启动后观察日志中的 stack monitor 输出：
# I (5000) stack_monitor: Free stack: heap=45KB, ipc0=512B, ipc1=520B, ...
```

---

## 📚 推荐阅读

### 文档
- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) - 系统设计深度解读
- [BUILD.md](./BUILD.md) - 编译与烧录完整指南
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - 日常速查表

### 外部资源
- [ESP-IDF 官方文档](https://docs.espressif.com/projects/esp-idf/)
- [Matter 协议规范](https://csa-iot.org/all-solutions/matter/)
- [FreeRTOS 教程](https://www.freertos.org/a00106.html)
- [MQTT 3.1.1 标准](http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html)

### 代码示例
- [ESP-IDF 示例](https://github.com/espressif/esp-idf/tree/master/examples)
- [Matter 示例](https://github.com/project-chip/connectedhomeip/tree/master/examples)

---

## 💡 常见问题 (FAQ)

**Q: 我改动了代码但编译失败？**  
A: 检查以下顺序：
1. 执行 `idf.py fullclean` 清理所有缓存
2. 查看错误消息是否提到 undefined reference（可能是 C/C++ 混编问题）
3. 检查是否修改了 CMakeLists.txt 但忘记添加新文件到 SRCS

**Q: 烧录后设备无法启动？**  
A: 
1. 检查 UART 连接是否正确
2. 尝试 `idf.py erase-flash` 擦除后重新烧录
3. 查看串口输出是否有 PANIC/FATAL 日志

**Q: RTC 无法同步时间？**  
A:
1. 验证网络连接正常
2. 检查 ip-api.com 是否可以访问
3. 查看 geo_locate 和 timezone_sync 的日志输出

**Q: MQTT 连接不上？**  
A:
1. 确认 broker emqx.io 可以 ping 通
2. 临时禁用证书验证以排查 TLS 问题
3. 检查网络是否被防火墙阻止 8883 端口

---

**最后更新**：2026-04-17  
**下一步**：选择一个简单任务（如"新增日志标签"）完成第一个 PR！
