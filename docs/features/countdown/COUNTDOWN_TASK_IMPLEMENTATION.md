## 倒计时任务管理模块实现指南

**日期**: 2026-04-21  
**模块**: Countdown Task Manager (倒计时任务管理)  
**状态**: ✅ 代码实现完成 | ⚠️ 编译待修复

---

## 1. 模块概述

### 1.1 功能定位

**问题**: 远端控制端（MQTT/UDP/BLE）需要向灯设备下发**定时任务**（如"明天14:30打开灯，亮度800"），本地灯设备需要在指定时间自动执行这些任务。

**解决方案**:
- 已接收 MQTT 与独立 UDP JSON 命令口下发的任务
- 将任务持久化存储到 NVS（断电不丢失）
- 后台定时检查，时间匹配时通过 state_manager 执行目标状态

### 1.2 核心特性

| 特性 | 描述 |
|------|------|
| 协议支持 | MQTT、UDP JSON 命令口；BLE 暂未支持完整倒计时下发 |
| 存储方式 | 消息队列 + NVS持久化 |
| 任务类型 | 单次、每日、每周 |
| 线程安全 | 互斥锁保护、无锁队列操作 |
| 检查周期 | 每秒检查一次（精度±1秒） |
| 断电保护 | NVS持久化，设备重启后恢复执行 |

---

## 2. 文件清单

### 2.1 新增文件

#### [main/app/countdown_task.h](../../../main/app/countdown_task.h)
**行数**: 107  
**内容**: 
- `CountdownTaskType` 枚举：ONCE(0)、DAILY(1)、WEEKLY(2)
- `CountdownTaskStatus` 枚举：PENDING、DONE、CANCELLED
- `countdown_task_t` 结构：任务主体，包含ID、类型、触发时间、目标设备状态、状态
- `countdown_task_message_t` 结构：队列消息（操作类型 + 任务体）
- 常量定义：队列长度(10)、最大任务数(16)、栈大小(4096)

**示例结构**:
```c
typedef struct {
    uint32_t task_id;                    // 任务唯一ID
    CountdownTaskType type;              // ONCE/DAILY/WEEKLY
    struct tm trigger_time;              // 触发时间
    device_state_t target_state;         // 执行目标状态
    CountdownTaskStatus status;          // 任务状态
    uint64_t created_timestamp;          // 创建时间戳
} countdown_task_t;
```

#### [main/app/app_countdown.h](../../../main/app/app_countdown.h)
**行数**: 99  
**内容**: 
- 初始化/反初始化函数
- 任务增删查改API（6个公开函数）
- 统计查询接口

**公开API**:
```c
esp_err_t app_countdown_init(void);
esp_err_t app_countdown_add_task(const countdown_task_t *task);
esp_err_t app_countdown_remove_task(uint32_t task_id);
esp_err_t app_countdown_query_task(uint32_t task_id, countdown_task_t *task);
esp_err_t app_countdown_clear_all_tasks(void);
uint16_t app_countdown_get_task_count(void);
esp_err_t app_countdown_get_stats(uint16_t *executed, uint16_t *pending, uint16_t *cancelled);
```

#### [main/app/app_countdown.c](../../../main/app/app_countdown.c)
**行数**: ~600  
**内容**: 
- 全局变量：消息队列、互斥锁、任务列表
- 内部函数：NVS载入/保存、时间匹配、任务执行
- 后台线程：`countdown_manager_thread()`
- API实现：初始化、任务操作、统计

**核心线程逻辑**:
```c
void countdown_manager_thread(void *arg) {
    countdown_load_from_nvs();  // 启动时恢复任务
    
    while (1) {
        // 1. 处理队列消息（ADD/REMOVE/CLEAR_ALL）
        if (xQueueReceive(...)) {
            // 添加/删除/清空任务，保存到NVS
        }
        
        // 2. 每秒检查一次是否有任务触发
        time_t now = time(NULL);
        localtime_r(&now, &timeinfo);
        for (uint16_t i = 0; i < g_task_count; i++) {
            if (countdown_is_time_match(&timeinfo, &g_task_list[i])) {
                countdown_execute_task(&g_task_list[i]);  // 调用 state_manager_update_state()
            }
        }
        
        vTaskDelay(pdMS_TO_TICKS(1000));  // 每秒循环一次
    }
}
```

### 2.2 修改文件

#### [main/CMakeLists.txt](main/CMakeLists.txt)
**修改**: 添加源文件
```cmake
idf_component_register(
    SRCS
        "main.cpp"
        "app/app_rtc.c"
        "app/app_countdown.c"  # ← 新增
        "utils/stack_monitor.c"
        ...
)
```

#### [main/main.cpp](main/main.cpp)
**修改**: 
1. 包含头文件
```cpp
#include "app/app_countdown.h"
```

2. 调用初始化函数
```cpp
extern "C" void app_main() {
    // ... 其他初始化 ...
    ESP_ERROR_CHECK(local_output_init());
    ESP_ERROR_CHECK(app_countdown_init());  // ← 新增
    stack_monitor_start();
    // ...
}
```

#### [main/Kconfig.projbuild](main/Kconfig.projbuild)
**修改**: 新增配置菜单
```kconfig
menu "Debug & Features"
    menu "Countdown Task Manager"
        config COUNTDOWN_TASK_ENABLE
            bool "Enable countdown task manager"
            default y
            
        config COUNTDOWN_MAX_TASKS
            int "Maximum concurrent countdown tasks"
            default 16
            range 1 64
            
        config COUNTDOWN_QUEUE_LENGTH
            int "Countdown message queue length"
            default 10
            
        config COUNTDOWN_TASK_STACK_SIZE
            int "Countdown manager task stack size (bytes)"
            default 4096
    endmenu
endmenu
```

---

## 3. 工作流程

### 3.1 时序图

```
┌─────────────────────────────────────────────────────────────┐
│ 远端控制端（MQTT/UDP/BLE）                                   │
│ 下发: {"task_id": 101, "trigger_time": "2026-04-22T14:30:00", ...}
└──────────────────┬──────────────────────────────────────────┘
                   │
         ┌─────────▼──────────┐
        │ 协议解析器         │
        │ (mqtt_agent /      │
        │  ambient_command)  │
         └─────────┬──────────┘
                   │
         ┌─────────▼──────────────────────────────┐
         │ app_countdown_add_task()                │
         │ 创建 countdown_task_message_t           │
         │ 推送到 g_countdown_queue                │
         └─────────┬──────────────────────────────┘
                   │
         ┌─────────▼──────────────────────────────┐
         │ countdown_manager_thread (FreeRTOS)    │
         │                                         │
         │ 1. xQueueReceive() 接收消息             │
         │ 2. 检查任务列表中是否已存在该ID         │
         │ 3. 添加任务到 g_task_list               │
         │ 4. countdown_save_to_nvs() 持久化       │
         └─────────┬──────────────────────────────┘
                   │
         ┌─────────▼──────────────────────────────┐
         │ 每秒时间检查循环                        │
         │                                         │
         │ time(&now);                            │
         │ localtime_r(&now, &timeinfo);          │
         │ 遍历 g_task_list，检查时间匹配         │
         └─────────┬──────────────────────────────┘
                   │
       ┌───────────▼──────────────┐
       │ 时间匹配成功             │
       │  ↓                       │
    │ state_manager_update_    │
    │ state()                  │
       │  ↓                       │
    │ local_output 回调        │
       │  ↓                       │
    │ light_control_bus /      │
    │ dev_lamp 驱动执行        │
       │  ↓                       │
       │ LED/PWM 硬件输出         │
       └──────────────────────────┘
```

### 3.2 时间匹配逻辑

| 任务类型 | 匹配条件 | 示例 |
|---------|---------|------|
| **TASK_TYPE_ONCE** | 年月日时分都相同 | 2026-04-22 14:30 只执行一次 |
| **TASK_TYPE_DAILY** | 每天时分相同 | 每天 14:30 都执行 |
| **TASK_TYPE_WEEKLY** | 每周同一天同时间 | 每周三 14:30 执行 |

### 3.3 持久化机制

```
┌──────────────────────┐
│ 启动时                │
│ countdown_load_from_nvs()
│ 从 NVS 恢复任务列表   │
│ → g_task_list[]       │
│ → g_task_count        │
└──────────┬───────────┘
           │
┌──────────▼───────────────────────────┐
│ 任务执行或状态变化时                  │
│ countdown_save_to_nvs()               │
│ 同步 g_task_list[] 到 NVS             │
│ NVS namespace: "countdown"             │
│ NVS key: "tasks"                       │
│ Blob size: 16 * sizeof(countdown_task_t)
└──────────────────────────────────────┘
```

---

## 4. 协议集成

### 4.1 MQTT 下发格式 (JSON)

**下发 Topic**: `iot/device/{MAC}/timer`

**回执 Topic**: `iot/device/{MAC}/timer_reply`

**Payload**:
```json
{
    "cmd": "add_timer",
  "task_id": 101,
    "type": "once",
  "trigger_time": "2026-04-22T14:30:00",
    "power": true,
    "mode": "cct",
    "lightness": 80,
    "cct": 5600
}
```

**已支持命令**:

```json
{ "cmd": "add_timer", "task_id": 101, "type": "once", "trigger_time": "2026-04-22T14:30:00", "power": true, "mode": "cct", "lightness": 80, "cct": 5600 }
{ "cmd": "remove_timer", "task_id": 101 }
{ "cmd": "clear_timer" }
{ "cmd": "query_timer", "task_id": 101 }
{ "cmd": "list_timer" }
{ "cmd": "stats_timer" }
```

**回执示例**:

```json
{ "action": "add_timer", "result": "ok", "task": { "task_id": 101, "type": "once", "status": "pending", "trigger_time": "2026-04-22T14:30:00", "target_state": { "power": true, "mode": "cct", "lightness": 80, "cct": 5600 } } }
```

```json
{ "action": "stats_timer", "result": "ok", "executed": 1, "pending": 2, "cancelled": 0, "total": 3 }
```

**处理流程**:
```c
// 在 mqtt_agent 订阅回调中
if (topic == "iot/device/<mac>/timer") {
        // 1. 解析 cmd / task_id / type / trigger_time / 状态字段
        // 2. add/remove/query/list/stats
        // 3. 发布到 iot/device/<mac>/timer_reply
}
```

### 4.2 UDP 下发格式 (JSON)

**监听端口**: `CONFIG_AMBIENT_COMMAND_PORT`，默认 `5569`

**Payload**:
```json
{ "cmd": "add_timer", "task_id": 101, "type": "once", "trigger_time": "2026-04-22T14:30:00", "power": true, "mode": "cct", "lightness": 80, "cct": 5600 }
```

**已支持命令**:
```json
{ "cmd": "add_timer", "task_id": 101, "type": "once", "trigger_time": "2026-04-22T14:30:00", "power": true, "mode": "cct", "lightness": 80, "cct": 5600 }
{ "cmd": "remove_timer", "task_id": 101 }
{ "cmd": "clear_timer" }
{ "cmd": "query_timer", "task_id": 101 }
{ "cmd": "list_timer" }
{ "cmd": "stats_timer" }
```

**处理流程**:
```c
// 在 ambient_command.c 中
if (strcmp(cmd, "add_timer") == 0) {
    countdown_task_t task = {0};
    state_manager_get_state(&task.target_state);
    apply_state_patch_from_json(root, &task.target_state);
    app_countdown_add_task(&task);
}
```

### 4.3 BLE/Matter 下发

**当前状态**:
- BLE 现有 mesh 包长固定为 10 字节，可用 body 仅 8 字节，无法完整承载 `task_id + trigger_time + target_state`。
- 因此本轮没有硬塞 BLE 倒计时协议，避免引入不可维护的半包状态机。
- 如果后续确实要支持 BLE，需要单独设计扩展协议，例如分片写入或 vendor-specific 长包通道。

### 4.4 UDP 联调脚本

**脚本路径**: `tools/udp_countdown_test.py`

**快速示例**:

```bash
# 1) 添加任务：90 秒后触发
python3 tools/udp_countdown_test.py add \
    --ip 192.168.9.105 \
    --task-id 101 \
    --in-seconds 90 \
    --power on \
    --mode cct \
    --lightness 80 \
    --cct 5600

# 2) 查询指定任务
python3 tools/udp_countdown_test.py query --ip 192.168.9.105 --task-id 101

# 3) 列出所有任务
python3 tools/udp_countdown_test.py list --ip 192.168.9.105

# 4) 查看统计
python3 tools/udp_countdown_test.py stats --ip 192.168.9.105

# 5) 删除任务
python3 tools/udp_countdown_test.py remove --ip 192.168.9.105 --task-id 101

# 6) 清空任务
python3 tools/udp_countdown_test.py clear --ip 192.168.9.105
```

**说明**:
- 默认端口为 `5569`，可用 `--port` 覆盖。
- 默认响应超时 `2s`，可用 `--timeout` 调整。
- `add` 支持 `--trigger-time` 直接传 ISO 时间；不传时用 `--in-seconds`（默认 90 秒）。

### 4.5 BLE 扩展协议草案（后续实现）

为兼容现有 10 字节 BLE mesh 报文，可采用**分片写入 + 提交**模式：

1. `TIMER_BEGIN`
    - 字段: `session_id(1B)`、`task_id(4B)`、`type(1B)`
2. `TIMER_CHUNK`
    - 字段: `session_id(1B)`、`seq(1B)`、`payload(<=6B)`
    - 按序发送 trigger_time 与 target_state 的二进制 TLV。
3. `TIMER_COMMIT`
    - 字段: `session_id(1B)`、`crc16(2B)`
    - 设备校验通过后调用 `app_countdown_add_task()`。
4. `TIMER_ABORT`
    - 字段: `session_id(1B)`，用于取消会话。

**设备端建议**:
- 仅维护 1~2 个并发 session，超时（如 3s）自动清理。
- COMMIT 成功后立即回执 `task_id/result`。
- 与 MQTT/UDP 保持同一语义集合（add/remove/query/list/stats），避免三套行为分叉。

---

## 5. 编译与配置

### 5.1 编译命令

```bash
# 完整清理 + 编译
idf.py fullclean
idf.py build

# 或增量编译
idf.py build
```

### 5.2 Kconfig 配置更新

```bash
# 重新配置（加载新的 Kconfig 选项）
idf.py reconfigure

# 或使用菜单编辑
idf.py menuconfig
# → Project Configuration → Debug & Features → Countdown Task Manager
```

### 5.3 编译状态

**✅ 代码实现完成**: 倒计时核心模块 + MQTT 定时命令 + UDP JSON 定时命令口

**⚠️ 当前构建风险**: 工程里仍有既有 Matter/connectedhomeip 编译问题风险
- **原因**: 非本次改动范围内的 Matter 侧告警/错误可能继续阻塞全量构建
- **临时解决**: 在构建前修复 Matter 警告或降低编译器警告级别
- **永久解决**: 更新 Matter 源码或修改 CMakeLists.txt 关闭 -Werror

---

## 6. API 使用示例

### 6.1 添加单次任务

```c
countdown_task_t task = {
    .task_id = 1001,
    .type = TASK_TYPE_ONCE,
    .trigger_time = {
        .tm_year = 126,   // 2026年 (从1900起)
        .tm_mon = 3,      // 4月
        .tm_mday = 22,    // 22日
        .tm_hour = 14,    // 14时
        .tm_min = 30,     // 30分
        .tm_sec = 0
    },
    .target_state = {
        .power_on = true,
        .matter_level = 203,
        .color.mode = LIGHT_MODE_CCT,
        .color.value.cct = {
            .cct = 5600,
            .lightness = 80.0f,
        },
    }
};

app_countdown_add_task(&task);
```

### 6.2 添加每日任务

```c
countdown_task_t task = {
    .task_id = 2001,
    .type = TASK_TYPE_DAILY,
    .trigger_time = {
        .tm_hour = 9,     // 每天 9:00
        .tm_min = 0,
        .tm_sec = 0
        // 其他字段忽略
    },
    .target_state = { /* ... */ }
};

app_countdown_add_task(&task);
```

### 6.3 查询任务

```c
countdown_task_t task;
esp_err_t err = app_countdown_query_task(1001, &task);
if (err == ESP_OK) {
    printf("Task %u status: %d\n", task.task_id, task.status);
}
```

### 6.4 统计信息

```c
uint16_t executed, pending, cancelled;
app_countdown_get_stats(&executed, &pending, &cancelled);
printf("Tasks: %u executed, %u pending, %u cancelled\n", 
       executed, pending, cancelled);
```

---

## 7. 常见问题 & 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|--------|
| 任务未在指定时间执行 | 1. 设备RTC时间不准确<br>2. 任务状态已为DONE | 1. 检查NTP同步<br>2. 查询任务状态 |
| 断电后任务丢失 | NVS未妥善保存 | 检查 countdown_save_to_nvs() 日志 |
| 队列满，任务被拒绝 | 并发请求过多 | 增加 COUNTDOWN_QUEUE_LENGTH |
| 内存超限 | 任务数超过限制 | 增加 MAX_COUNTDOWN_TASKS_IN_MEMORY 或删除旧任务 |

---

## 8. 后续优化方向

| 优化项 | 优先级 | 估计工作量 | 备注 |
|-------|-------|---------|------|
| CRON表达式支持 | 高 | 2-3天 | 如 "0 14 * * 1-5"（工作日14:00） |
| 条件执行 | 中 | 1-2天 | 基于传感器/网络状态 |
| 任务链（多步骤） | 中 | 2-3天 | 如 先开灯→等待5秒→改色温 |
| 远端查询接口 | 低 | 1天 | 支持查询已设置的任务列表 |
| 执行失败重试 | 低 | 1天 | 最多重试3次 |
| GUI界面（Web） | 中 | 3-5天 | 用于管理任务 |

---

## 9. 测试检查清单

- [ ] 编译成功（解决 Matter 警告）
- [ ] 单次任务按时执行
- [ ] 每日任务每天重复执行
- [ ] 每周任务按星期匹配执行
- [ ] 断电重启后任务恢复
- [ ] NVS达到容量上限时的处理
- [ ] 并发添加/删除操作的线程安全性
- [ ] MQTT/UDP 协议集成测试
- [ ] BLE 扩展协议方案评审
- [ ] 时间同步失败时的行为
- [ ] 长期稳定性运行（24小时+）

---

## 10. 文件关系图

```
main/main.cpp
  ├─ #include "app/app_countdown.h"
  └─ app_countdown_init()
      │
      └─ FreeRTOS task: countdown_manager_thread()
          │
          ├─ 处理消息队列 (xQueueReceive)
          │   └─ MQTT/UDP/BLE 协议下发的任务
          │
          ├─ NVS 持久化 (countdown_save_to_nvs)
          │   └─ components/nvs_flash
          │
          └─ 时间检查 + 执行
              ├─ time(), localtime_r()
              ├─ 时间匹配算法
              └─ state_manager_update_state()
                  └─ local_output_on_state_event()
                      └─ light_control_bus_publish_command()
                          └─ dev_lamp 驱动
                              └─ LED/PWM 输出
```

---

**文档版本**: 1.0  
**最后更新**: 2026-04-21  
**作者**: AI Assistant  
**审核者**: 待定
