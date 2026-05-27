# ESP32S3 智能灯具 - 核心代码框架

## 1. 状态管理器 (state_manager.h)

```c
#ifndef STATE_MANAGER_H
#define STATE_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include <time.h>

// 设备状态结构体
typedef struct {
    // 电源与亮度
    bool power_on;
    uint8_t brightness;          // 0-100%
    
    // 色温与颜色
    uint16_t color_temp;         // 2700K-6500K
    uint8_t color_x;             // CIE 颜色坐标
    uint8_t color_y;
    
    // 工作模式
    enum {
        MODE_NORMAL,             // 正常
        MODE_BREATHING,          // 呼吸灯
        MODE_BLINK,              // 闪烁
        MODE_RAINBOW,            // 彩虹
        MODE_CUSTOM              // 自定义
    } mode;
    
    // 版本控制与时间戳
    uint32_t version;            // 中断环路关键字段
    uint64_t timestamp;          // 毫秒时间戳
    uint8_t last_source;         // 最后修改源(0=本地,1=MQTT,2=Matter,...)
    
    // 统计数据
    uint32_t power_on_duration;  // 开启持续时间(秒)
    uint32_t power_cycle_count;  // 开关次数
    
} device_state_t;

// 事件回调函数类型
typedef void (*state_changed_callback_t)(const device_state_t *old_state, 
                                         const device_state_t *new_state);

// 状态管理器初始化
esp_err_t state_manager_init(void);

// 获取当前状态（线程安全）
device_state_t state_manager_get_state(void);

// 更新状态（线程安全）
esp_err_t state_manager_set_state(const device_state_t *new_state, uint8_t source);

// 更新单个字段
esp_err_t state_manager_set_brightness(uint8_t brightness, uint8_t source);
esp_err_t state_manager_set_power(bool power, uint8_t source);
esp_err_t state_manager_set_color_temp(uint16_t temp, uint8_t source);
esp_err_t state_manager_set_mode(uint8_t mode, uint8_t source);

// 注册状态变化监听器
esp_err_t state_manager_on_change(state_changed_callback_t callback);

// 状态持久化到NVS
esp_err_t state_manager_save_to_nvs(void);
esp_err_t state_manager_load_from_nvs(void);

// 清除所有回调
void state_manager_clear_callbacks(void);

// 获取状态历史
esp_err_t state_manager_get_history(device_state_t *history_buffer, 
                                    uint32_t buffer_size,
                                    uint32_t *count);

#endif
```

## 2. 核间通信管理器 (ipc_manager.h)

```c
#ifndef IPC_MANAGER_H
#define IPC_MANAGER_H

#include <stdint.h>
#include "state_types.h"

// IPC消息类型
typedef enum {
    IPC_MSG_STATE_UPDATE,        // 状态更新
    IPC_MSG_CONTROL_COMMAND,     // 控制命令
    IPC_MSG_NETWORK_STATUS,      // 网络状态
    IPC_MSG_PROTOCOL_EVENT,      // 协议事件
    IPC_MSG_ERROR,               // 错误报告
    IPC_MSG_DIAGNOSTIC,          // 诊断信息
} ipc_msg_type_t;

// IPC消息结构体
typedef struct {
    ipc_msg_type_t type;
    uint32_t timestamp;
    uint8_t priority;            // 0-3, 数字越大优先级越高
    uint16_t payload_len;
    uint8_t payload[256];        // 灵活的负载
} ipc_message_t;

// 初始化IPC队列
esp_err_t ipc_manager_init(void);

// CPU0 -> CPU1: 发送消息
esp_err_t ipc_send_to_cpu1(const ipc_message_t *msg);

// CPU1 -> CPU0: 发送消息
esp_err_t ipc_send_to_cpu0(const ipc_message_t *msg);

// 接收消息（阻塞，带超时）
esp_err_t ipc_receive(ipc_message_t *msg, uint32_t timeout_ms);

// 消息队列获取剩余空间
uint32_t ipc_get_queue_free_space(void);

// 消息序列化/反序列化
esp_err_t ipc_serialize_state(const device_state_t *state, 
                              uint8_t *buffer, 
                              uint16_t *len);

esp_err_t ipc_deserialize_state(const uint8_t *buffer, 
                                uint16_t len,
                                device_state_t *state);

#endif
```

## 3. 协议分发器 (protocol_dispatcher.h)

```c
#ifndef PROTOCOL_DISPATCHER_H
#define PROTOCOL_DISPATCHER_H

#include "state_types.h"

// 协议类型定义
typedef enum {
    PROTOCOL_MQTT = 0,
    PROTOCOL_MATTER = 1,
    PROTOCOL_UDP = 2,
    PROTOCOL_BLE = 3,
    PROTOCOL_LOCAL = 4,          // 本地输出
} protocol_type_t;

// 分发器初始化
esp_err_t protocol_dispatcher_init(void);

// 分发状态变化到所有协议
// skip_protocol: 跳过某个协议（-1表示不跳过）
esp_err_t protocol_dispatcher_publish_state(const device_state_t *state, int skip_protocol);

// 协议注册/注销
typedef esp_err_t (*protocol_handler_t)(const device_state_t *state);

esp_err_t protocol_dispatcher_register(protocol_type_t protocol, 
                                      protocol_handler_t handler);

esp_err_t protocol_dispatcher_unregister(protocol_type_t protocol);

// 获取协议状态
bool protocol_dispatcher_is_online(protocol_type_t protocol);
bool protocol_dispatcher_is_ready(protocol_type_t protocol);

// 获取在线协议数
uint8_t protocol_dispatcher_get_online_count(void);

// 防环路检测
bool protocol_dispatcher_should_forward(const device_state_t *new_state,
                                       const device_state_t *last_state,
                                       protocol_type_t source,
                                       protocol_type_t target);

#endif
```

## 4. MQTT任务框架 (mqtt_task.c 伪代码)

```c
#include "mqtt_client.h"
#include "ipc_manager.h"
#include "protocol_dispatcher.h"

#define MQTT_BROKER_URI      "mqtt://mqtt.example.com"
#define MQTT_BROKER_PORT     1883
#define MQTT_CLIENT_ID       "light-%s"  // MAC地址后缀

static esp_mqtt_client_handle_t mqtt_client = NULL;

// MQTT 事件处理
static void mqtt_event_handler(void *handler_args, esp_event_base_t base, 
                               int32_t event_id, void *event_data)
{
    esp_mqtt_event_handle_t event = event_data;
    
    switch(event->event_id) {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI(TAG, "MQTT Connected");
            // 订阅控制主题
            esp_mqtt_client_subscribe(mqtt_client, "light/control", 0);
            esp_mqtt_client_subscribe(mqtt_client, "light/command", 0);
            break;
            
        case MQTT_EVENT_DISCONNECTED:
            ESP_LOGI(TAG, "MQTT Disconnected");
            break;
            
        case MQTT_EVENT_DATA:
            // 处理接收到的消息
            mqtt_handle_message(event);
            break;
            
        case MQTT_EVENT_ERROR:
            ESP_LOGE(TAG, "MQTT Error");
            break;
    }
}

// 处理MQTT接收消息
static void mqtt_handle_message(esp_mqtt_event_handle_t event)
{
    // 1. 解析JSON消息
    device_state_t new_state;
    if (mqtt_parse_command(event->data, event->data_len, &new_state) != ESP_OK) {
        return;
    }
    
    // 2. 防环路检查
    device_state_t current_state = state_manager_get_state();
    if (!protocol_dispatcher_should_forward(&new_state, &current_state, 
                                           PROTOCOL_MQTT, PROTOCOL_LOCAL)) {
        return;  // 丢弃消息
    }
    
    // 3. 更新状态管理器
    state_manager_set_state(&new_state, PROTOCOL_MQTT);
    
    // 4. 发送IPC消息到CPU1
    ipc_message_t msg = {
        .type = IPC_MSG_STATE_UPDATE,
        .timestamp = esp_timer_get_time() / 1000,
        .priority = 2,
    };
    ipc_serialize_state(&new_state, msg.payload, &msg.payload_len);
    ipc_send_to_cpu1(&msg);
    
    // 5. 分发到其他协议
    protocol_dispatcher_publish_state(&new_state, PROTOCOL_MQTT);
}

// MQTT 发布状态变化
void mqtt_publish_state(const device_state_t *state)
{
    cJSON *root = cJSON_CreateObject();
    cJSON_AddBoolToObject(root, "power_on", state->power_on);
    cJSON_AddNumberToObject(root, "brightness", state->brightness);
    cJSON_AddNumberToObject(root, "color_temp", state->color_temp);
    cJSON_AddNumberToObject(root, "version", state->version);
    
    char *payload = cJSON_Print(root);
    esp_mqtt_client_publish(mqtt_client, "light/status", payload, 0, 1);
    
    free(payload);
    cJSON_Delete(root);
}

// MQTT任务主循环
void mqtt_task(void *arg)
{
    // 1. 初始化MQTT客户端
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = MQTT_BROKER_URI,
        .credentials.client_id = "light-" DEVICE_MAC,
    };
    
    mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(mqtt_client, ESP_EVENT_ANY_ID, 
                                   mqtt_event_handler, NULL);
    esp_mqtt_client_start(mqtt_client);
    
    // 2. 注册协议分发器
    protocol_dispatcher_register(PROTOCOL_MQTT, mqtt_publish_state);
    
    // 3. 监听状态变化
    state_manager_on_change(mqtt_on_state_changed);
    
    // 4. 主循环
    while(1) {
        vTaskDelay(pdMS_TO_TICKS(1000));  // 保活心跳
    }
}
```

## 5. 本地任务管理 (local_manager.c 伪代码)

```c
#include "input_system.h"
#include "output_system.h"
#include "scheduler.h"
#include "ipc_manager.h"

// CPU1本地管理任务
void local_manager_task(void *arg)
{
    // 初始化各子系统
    input_system_init();
    output_system_init();
    scheduler_init();
    
    ESP_LOGI(TAG, "Local Manager running on CPU1");
    
    while(1) {
        // 1. 处理输入事件
        input_event_t input_event;
        if (input_system_get_event(&input_event, pdMS_TO_TICKS(100)) == ESP_OK) {
            handle_input_event(&input_event);
        }
        
        // 2. 处理定时/循环任务
        scheduler_run_tick();
        
        // 3. 处理来自CPU0的IPC消息
        ipc_message_t ipc_msg;
        if (ipc_receive(&ipc_msg, 0) == ESP_OK) {  // 非阻塞
            handle_ipc_message(&ipc_msg);
        }
        
        // 4. 更新输出
        output_system_apply_state(&current_state);
    }
}

// 处理输入事件
static void handle_input_event(const input_event_t *event)
{
    device_state_t new_state = state_manager_get_state();
    
    switch(event->type) {
        case INPUT_TYPE_BUTTON_PRESS:
            if (event->key_id == KEY_POWER) {
                // 切换电源
                new_state.power_on = !new_state.power_on;
                new_state.version++;
                new_state.timestamp = esp_timer_get_time() / 1000;
                state_manager_set_state(&new_state, PROTOCOL_LOCAL);
            }
            break;
            
        case INPUT_TYPE_SENSOR_CHANGE:
            // 根据光照调整亮度
            if (event->sensor_id == SENSOR_LIGHT) {
                new_state.brightness = adjust_brightness_based_on_light(event->value);
                state_manager_set_state(&new_state, PROTOCOL_LOCAL);
            }
            break;
    }
}

// 处理来自CPU0的IPC消息
static void handle_ipc_message(const ipc_message_t *msg)
{
    switch(msg->type) {
        case IPC_MSG_STATE_UPDATE: {
            device_state_t state;
            ipc_deserialize_state(msg->payload, msg->payload_len, &state);
            // 不更新本地状态，直接应用输出
            output_system_apply_state(&state);
            break;
        }
        
        case IPC_MSG_NETWORK_STATUS:
            // 处理网络状态变化
            on_network_status_changed(msg);
            break;
    }
}

// 输出系统应用状态
static void output_system_apply_state(const device_state_t *state)
{
    if (state->power_on) {
        // 设置亮度
        pwm_set_brightness(state->brightness);
        
        // 设置色温
        color_temp_set(state->color_temp);
        
        // 执行动画
        switch(state->mode) {
            case MODE_BREATHING:
                animation_breathing_start(state->brightness);
                break;
            case MODE_BLINK:
                animation_blink_start();
                break;
            default:
                animation_stop();
        }
    } else {
        // 开关灯熄灭
        pwm_set_brightness(0);
        animation_stop();
    }
}
```

## 6. 应用入口 (app.c)

```c
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "system_init.h"

void app_main(void)
{
    ESP_LOGI(TAG, "=== SmartLight Application Start ===");
    
    // 1. 系统初始化
    system_init_common();
    
    // 2. 状态管理器初始化
    state_manager_init();
    state_manager_load_from_nvs();
    
    // 3. IPC管理器初始化
    ipc_manager_init();
    
    // 4. CPU0: 网络任务
    xTaskCreatePinnedToCore(
        mqtt_task,
        "mqtt_task",
        8192,
        NULL,
        10,
        NULL,
        0  // CPU0
    );
    
    xTaskCreatePinnedToCore(
        ble_task,
        "ble_task",
        8192,
        NULL,
        9,
        NULL,
        0  // CPU0
    );
    
    xTaskCreatePinnedToCore(
        network_manager_task,
        "network_mgr",
        4096,
        NULL,
        15,
        NULL,
        0  // CPU0
    );
    
    // 5. CPU1: 本地业务任务
    xTaskCreatePinnedToCore(
        local_manager_task,
        "local_mgr",
        8192,
        NULL,
        10,
        NULL,
        1  // CPU1
    );
    
    ESP_LOGI(TAG, "All tasks created, system ready");
}
```

## 7. CMakeLists.txt 示例

```cmake
cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

project(SmartLight)

# 组件目录
set(COMPONENTS_DIR "${CMAKE_SOURCE_DIR}/components")

# 标准IDF组件
set(EXTRA_COMPONENT_DIRS 
    ${COMPONENTS_DIR}
)

idf_build_process(esp32s3
    COMPONENTS 
        main
        esp_mqtt
        nvs_flash
        wifi
        bt
        state_manager
        ipc_manager
        protocol_dispatcher
)
```

---

## 使用建议

1. **状态管理为中心**：所有数据变化都经过 `state_manager`
2. **版本号防环**：确保每次数据变化都增加版本号
3. **时间戳记录**：便于调试和冲突解决
4. **核心亲和性**：使用 `xTaskCreatePinnedToCore` 绑定任务到特定核心
5. **优雅降级**：网络断开时，本地业务继续正常运行


---

## 6. 多源并发命令仲裁架构（2026-05-21 更新）

### 6.1 问题背景

本工程支持 Matter、MQTT、UDP、BLE 四条协议同时下发命令。在未整理前存在两条独立命令路径：

| 路径 | 覆盖协议 | 是否经过 state_manager |
|------|---------|----------------------|
| 受管路径 | Matter / MQTT / UDP | ✅ 是 |
| 旁路路径 | BLE | ❌ 否（直连 light_control_bus） |

旁路路径导致 BLE 命令改灯后，Matter/MQTT 侧状态快照过期，下次上报会发送错误值。

### 6.2 已实施的修复

**P0 — BLE 命令状态同步**（`main/app/app_bluetooth.c`）

在所有调用 `light_control_bus_publish_command(BLUETOOTH)` 的函数之后，额外通过新增的 `ble_sync_state_from_ctrl()` 静态函数将 `struct light_ctrl` 映射回 `device_state_t`，再调用：
```c
state_manager_update_state(&state, STATE_SOURCE_BLE);
protocol_dispatch_state(&state, STATE_SOURCE_BLE);
```
硬件输出路径（`light_control_bus`）不变，只增加状态快照同步和协议扇出。
覆盖命令类型：CCT/HSI/XY/GEL/RGBWW（common_light）、FX 特效、PFX 特效、亮度快调（light_bright）、电源开关（sleep_mode）。
同时同步 `matter_level`，避免 BLE 调光后 Matter Level Cluster 显示旧值。

**P1 — 来源优先级仲裁层**（`components/framework/state_manager/src/state_manager.c`）

在 `state_manager_update_state()` 的锁内加入来源优先级比较，拒绝低优先级来源对高优先级来源状态的覆写：

```
MATTER(3) > MQTT(2) = UDP(2) > BLE(1) > LOCAL(0)
```

- `STATE_SOURCE_LOCAL` 永远允许写入（保证上电初始化和出厂复位不被阻断）。
- 高优先级来源（如 Matter）设置状态后，低优先级来源会在 30 秒衰退窗口内被阻断；超过窗口后允许重新写入，避免“永久锁定”。
- 返回 `ESP_ERR_NOT_ALLOWED` 表示被仲裁拒绝，调用方可选择记录日志或忽略。

**P2 — 协议扇出去抖**（`components/framework/protocol_dispatcher/src/protocol_dispatcher.c`）

在 `protocol_dispatch_state()` 的 per-protocol 循环中加入 50ms 抑制窗口（`PROTOCOL_DISPATCH_DEBOUNCE_US = 50000`）：同一协议目标在 50ms 内不重复发送 IPC 消息，防止快速变更场景下的 IPC 队列积压。

### 6.3 统一命令路径示意

```
BLE/Matter/MQTT/UDP
        │
        ▼
  命令解析层（各协议 handler）
        │
        ├── 硬件输出：light_control_bus_publish_command(INTERNAL/BLUETOOTH/...)
        │       └──> CPU1 light_control_facade → 驱动层
        │
        └── 状态快照：state_manager_update_state(STATE_SOURCE_xxx)
                │  [拒绝低优先级写入]
                │
                ├── local_output_on_state_event → light_control_bus(INTERNAL)
                ├── matter_report_state_change → schedule_matter_sync
                └── protocol_dispatch_state(source)
                        │  [50ms 去抖]
                        └──> IPC → MQTT(CPU0) / UDP(CPU0) / Matter(CPU0)
```

### 6.4 仍存在的差距（待未来版本处理）

- **Button 源**：已并入统一状态链路，按钮电源切换走 `state_manager_update_state(STATE_SOURCE_LOCAL)`。
- **point_on_off / RS485**：`sys_status.point_on_off` 存于 `state_store` 影子路径，未合并进 `device_state_t`。
- **FX/特效模式**：`LIGHT_MODE > LIGHT_MODE_PWM` 的帧动画指令仅同步首帧 ctrl 结构，不能完整表达序列状态。
- **优先级解锁策略**：当前采用 30 秒衰退窗口，不是永久优先级锁；后续若要更细粒度控制，可引入“会话占用”或“显式释放”机制。
