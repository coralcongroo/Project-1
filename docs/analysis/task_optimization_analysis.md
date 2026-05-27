# 功能任务优化分析报告

## 0. 二次校准（基于当前源码）

本节用于修正第一版分析中的泛化结论，全部依据当前仓库源码扫描结果。

### 0.1 已确认的任务创建点

- 应用任务：
   - `app_power`：`main/app/app_power.c` 中以 `xTaskCreate(..., 1024 * 8, ..., configMAX_PRIORITIES - 1, ...)` 创建。
   - `app_light`：`main/app/app_light.c` 中以 `xTaskCreate(..., 1024 * 4, ..., configMAX_PRIORITIES - 2, ...)` 创建。
   - `app_rtc`：`main/app/app_rtc.c` 中以 `xTaskCreate(..., 1024 * 4, ..., configMAX_PRIORITIES - 1, ...)` 创建。
   - `app_use_btn`：`main/app/app_use_btn.c` 中以 `xTaskCreate(..., 1024 * 2, ..., configMAX_PRIORITIES - 2, ...)` 创建。
   - `db`：`main/app/app_local_db.c` 中以 `xTaskCreate(..., 2048, ..., configMAX_PRIORITIES - 1, ...)` 创建。
   - `rs485_master`：`main/app/app_rs485_master.c` 中以 `RS485_TASK_STACK_SIZE`（4KB）创建。

- 设备/特效任务（由 `drv_lamp_init` 拉起）：
   - `lamp_task`、`lamp_pwm_task`、`sidusfx`、`pixel_fx`，位于 `components/dev_lamp/dev_lamp.c`。
   - 其中 `pixel_fx` 采用 6KB 栈（`1024 * 6`），其余使用宏定义栈值。

- 网络任务：
   - `ambient_rx`：`components/cmd_wifi/ambient_receiver.c`。
   - `ambient_out`：`components/cmd_wifi/ambient_output.c`。
   - 任务参数由 `components/cmd_wifi/include/ambient_config.h` 提供默认值：
      - `CONFIG_AMBIENT_RECV_TASK_STACK_SIZE = 10KB`
      - `CONFIG_AMBIENT_OUTPUT_TASK_STACK_SIZE = 10KB`
      - `CONFIG_AMBIENT_RECV_TASK_PRIORITY = 5`
      - `CONFIG_AMBIENT_OUTPUT_TASK_PRIORITY = 6`

### 0.2 当前结构性风险（剩余项）

1. 网络任务优先级关系值得复测
- 当前 `ambient_out(6) > ambient_rx(5)`。
- 如果输出路径（`disp_flush` + `disp_show`）偶发阻塞，可能压制接收任务调度，导致收包抖动。

### 0.3 可立即执行的低风险优化

1. 先做“测量闭环”，再改栈
- 保持现有栈值，先连续采样 30~60 分钟 `uxTaskGetSystemState` 水位。
- 规则建议：`最小剩余栈 > 25%` 才可缩栈；缩栈后重复同样场景压测。

2. 优先优化 `app_power` 的动态分配
- 在 FFT 循环中存在频繁分配/释放缓存。
- 建议先改为复用缓冲区（静态或模块级复用），通常比“直接缩栈”更稳妥，且对实时性收益更直接。

3. 网络链路先做优先级 A/B 测试
- 场景 A：保持 `rx=5,out=6`。
- 场景 B：改为 `rx=6,out=5`。
- 采集指标：平均帧间隔、最大帧间隔、超时次数、丢帧次数。

4. 基于统一目录再做结构级优化
- 当前 `main/` 根目录已只保留 `main.c` 与组件元文件，任务参数调整可直接基于 `main/app/`、`main/utils/` 中的唯一实现继续推进。

### 0.4 建议执行顺序（按投入产出）

1. 去重并确定唯一编译路径（`main/` vs `main/app/`）。
2. 保留一份 `stack_monitor` 并加上关键任务白名单统计输出。
3. 对 `app_power` 做缓冲复用改造。
4. 对 `ambient_rx/ambient_out` 做优先级 A/B 压测。
5. 基于实测水位再做栈收缩。

### 0.5 已实施进展（本轮）

1. 编译入口已切到分层目录
- `main/CMakeLists.txt` 已调整为：
   - 固定包含 `main.c`
   - 递归包含 `app/`、`boot/`、`light/`、`utils/`、`proto/` 下的 `.c`
- 目的：确保所有业务实现均从功能子目录编译，`main/` 根目录不再承载业务代码。

2. 关键头文件已补齐类型依赖
- 已为 `light_control_bus.h`、`state_store.h` 补充 `los_data.h` 依赖。
- 已补齐 `main/app/app_light.h` 的结构体声明依赖与对外接口声明。
- 结果：分层源码编译路径可用。

3. stack monitor 已增强为可量化输出
- 文件：`main/utils/stack_monitor.c`
- 新增能力：
   - 关键任务白名单输出（app_power、ambient_rx、ambient_out、db、lamp_task 等）
   - 依据已知栈配置估算 `used%`（已用栈比例）
   - 低栈预警（默认阈值 `<512B`）
   - 全局最小水位摘要（lowest watermark）

4. 构建验证
- 已完成 `idf.py build`，结果 `Project build complete`。

5. app_power FFT 路径已完成首轮降开销改造
- 文件：`main/app/app_power.c`
- 已实施：
   - 将 RFFT 工作缓冲由“循环内动态分配释放”改为“一次初始化、循环复用”。
   - 将 RFFT 句柄由“每次调用 init/deinit”改为“任务启动时初始化后复用”。
   - 启动失败时任务主动退出并打印错误，避免空指针路径。
- 预期收益：
   - 降低堆碎片风险。
   - 降低 10ms 周期任务中的分配器开销与抖动。
   - 为后续缩栈评估提供更稳定基线。

6. 本轮验证
- 已再次执行 `idf.py build`，结果 `Project build complete`。

### 0.6 下一步执行指引（基于新监控）

建议先运行 30~60 分钟典型场景（蓝牙控灯 + UDP 显示 + 按键 + RS485 空闲/活跃），采集以下日志字段：

- `task=... free_min=... used~...%`
- `LOW STACK task=...`
- `lowest watermark: task=... free_min=...`

按如下阈值决策：

1. `free_min < 512B`
- 暂停该任务的缩栈计划，优先排查局部栈峰值路径。

2. `used~` 长期低于 `60%`
- 可作为第一批缩栈候选（建议每次缩减 512B 或 1KB）。

3. `ambient_out` 与 `ambient_rx` 之一长期接近阈值
- 优先做优先级 A/B 对比，不直接缩栈。


## 1. 当前任务配置总览

### 任务列表与资源使用

| 任务名称 | 栈大小 | 优先级 | 功能描述 |
|---------|--------|--------|---------|
| **app_light** | 4KB | configMAX_PRIORITIES-2 | 本地灯控处理 |
| **app_power** | 8KB | configMAX_PRIORITIES-1 | 音频采样+FFT计算 |
| **app_rtc** | 4KB | configMAX_PRIORITIES-1 | 网络时间同步 |
| **app_use_btn** | 2KB | configMAX_PRIORITIES-2 | 按键扫描 |
| **rs485_master** | 4KB | (默认) | RS485通信 |
| **db** | 2KB | configMAX_PRIORITIES-1 | NVS数据库操作 |
| **ambient_rx** | 10KB | 5 | Wi-Fi UDP接收 |
| **ambient_out** | 10KB | 6 | 灯带输出渲染 |
| **console** | (主线程) | 1 | 调试命令行 |

**总堆栈用量**：~51KB（应用任务部分）

---

## 2. 各任务优化空间分析

### 2.1 app_power (8KB) - 音频FFT任务 ⚠️ **高优化潜力**

**当前状况**：
- 栈大小最大（8KB）
- 执行频率：约每10ms处理一次FFT
- 操作：ADC采样 → FFT变换 → 频谱提取

**优化空间**：

1. **内存分配策略**
   ```cpp
   // 当前方式：每次分配
   int16_t *x = heap_caps_aligned_alloc(16, nfft * sizeof(int16_t) * 2);
   // 优化：预分配+复用
   static int16_t fft_buffer[FFT_SIZE * 2] __attribute__((aligned(16)));
   ```
   **收益**：减少堆碎片，降低每帧开销

2. **FFT缩放指数动态调整**
   ```cpp
   // 当前方式：固定缩放
   int in_exponent = MAX_EXPONENT - 6 * audio_Sensitivity / 100;
   // 优化：记忆式缓存上一次结果
   ```
   **收益**：减少计算，降低延迟

3. **频谱分析精度vs速度**
   - 当前：分10个频段，遍历所有FFT点
   - 建议：根据光效模式动态调整分辨率
     - 音乐同步光效：5个频段即可
     - 测试/调试模式：保留10段
   **收益**：20-30%CPU时间节省

4. **栈大小优化**
   - 当前8KB可能存在浪费
   - 建议：使用`stack overflow`检测工具量化
   - 目标：降至6KB

---

### 2.2 ambient_rx & ambient_out (各10KB) - 网络显示任务 ⚠️ **中等优化潜力**

**当前状况**：
- 接收任务：等待UDP数据包，解析，提交给输出任务
- 输出任务：等待最新帧，渲染WS28xx灯带

**优化空间**：

1. **栈大小重新评估**
   ```cpp
   // 当前各10KB，为安全余量设置
   // 建议：实际测量+20%安全系数
   ```
   - ambient_rx 实际用途：socket操作+协议解析
   - 预估精简目标：6-7KB
   - ambient_out 实际用途：SPI编码+输出
   - 预估精简目标：4-6KB
   
   **收益**：减少6-8KB内存占用

2. **缓冲区大小优化**
   ```cpp
   #define CONFIG_AMBIENT_MAX_FRAME_SIZE 2048  // 当前值
   // 分析：实际灯数 = 462 × 4B = 1848B
   // 建议：降至 1900B（+头部）或2000B
   ```
   **收益**：节省48B+其他开销

3. **优先级安排**
   - ambient_out (优先级6) > ambient_rx (优先级5)
   - **风险**：接收被输出打断，可能丢包
   - **建议**：评估是否需要倒转优先级 或 使用中断
   **收益**：降低丢包率 或 响应延迟

4. **轮询 vs 中断**
   - 当前：阻塞等待+超时轮询
   - 建议：UDP超时配置 + socket selec()
   ```cpp
   // 当前示意伪代码
   recvfrom(socket, buffer, size, 0, ...);  // 阻塞
   // 优化
   fd_set readset;
   struct timeval tv;
   select(socket+1, &readset, NULL, NULL, &tv);  // 高效等待
   ```
   **收益**：减少CPU空转，改善功耗

---

### 2.3 app_light (4KB) - 本地灯控任务 ⚠️ **低优化潜力**

**当前状况**：
- 处理light_control_bus发布的命令
- 调用light_control_facade计算灯控参数
- 发送给dev_lamp驱动

**优化空间**：

1. **命令队列** vs **事件驱动**
   - 当前架构：总线 → 队列 → 任务处理
   - 评估：是否存在频繁唤醒+高延迟情况
   - 建议：若不存在 → 降低优先级，改为事件触发
   **收益**：CPU时间 5-10%节省

2. **颜色计算缓存**
   - 若同一CCT多次请求 → 缓存上一次结果
   ```cpp
   static struct {
       uint16_t cct;
       float gm;
       struct mixing_pwm pwm;  // 缓存结果
   } color_cache;
   ```
   **收益**：快速响应重复请求

---

### 2.4 app_rtc (4KB) - 时间同步任务 ⚠️ **低优化潜力**

**当前状况**：
- 定期通过网络同步系统时间
- 标准SNTP流程，不频繁执行

**优化建议**：
1. 考虑启用轻睡眠 (light sleep) 期间
2. 同步频率调整：从几秒→几分钟
3. 栈大小4KB可能可降至3KB

**收益**：内存 0.5KB，CPU <1%

---

### 2.5 app_use_btn (2KB) - 按键扫描任务 ✅ **最小优化潜力**

**当前状况**：
- 栈大小已较小（2KB）
- 扫描周期固定（通常10-20ms）
- 优先级适当

**优化建议**：
1. 若按键不频繁 → 改为GPIO中断 + 软件消抖
   - 可降低功耗和CPU占用
2. 若需保留定时扫描 → 评估扫描周期
   - 过快：浪费CPU（>50Hz无人感知区别）
   - 过慢：响应延迟明显

**收益**：CPU 10-20%节省（若改为中断）

---

### 2.6 rs485_master (4KB) - RS485通信任务 ⚠️ **中等优化潜力**

**当前状况**：
- 处理RS485通信
- 未指定优先级（使用默认）

**优化空间**：
1. **优先级调整**
   - 建议：若是固件升级 → 降低优先级（避免打断实时任务）
   - 若是实时命令 → 提升优先级

2. **通信超时**
   - 评估：是否存在长时间阻塞
   - 建议：添加看门狗或超时自动返回

3. **栈大小验证**
   ```
   当前4KB，评估是否足够处理分片等
   ```

---

### 2.7 database (2KB) - NVS任务 ✅ **非常规任务**

**特性**：
- 仅在需要时创建
- 优先级最高（configMAX_PRIORITIES-1）
- 栈超小（2KB）

**优化建议**：
1. 异步缓存 - 不必每次都同步NVS
   ```cpp
   // 当前：立即写入NVS
   nvs_set_u32(handle, key, value);
   // 优化：缓存+定期同步
   state_cache[key] = value;
   // 后台任务定期 flush to NVS
   ```
   **收益**：降低延迟，避免UI阻塞

2. NVS分区大小评估
   - 当前：默认大小
   - 建议：统计实际写入量，合理规划

---

## 3. 优先级调度分析

### 当前优先级分布

```
Priority | Tasks
   5     | ambient_rx (Wi-Fi接收)
   6     | ambient_out (灯带输出)
  MAX-1  | app_power, app_rtc, db (高优先级)
  MAX-2  | app_light, app_use_btn (中高优先级)
  默认   | cmd_wifi, cmd_system, console等
  1      | console 主循环
```

### 问题识别

1. **实时性倒序** ⚠️
   - ambient_out (优先级6) > ambient_rx (优先级5)
   - 若输出任务阻塞，接收可能丢包
   - **建议**：考虑使用 `xSemaphoreGive/Take` 协调

2. **应用任务优先级偏高**
   - app_power (MAX-1)：音乐播放不必最高
   - **建议**：降至 MAX-3 或 MAX-4
   - **理由**：避免饥饿低优先级任务

3. **缺少任务间协调机制**
   - 当前：各任务独立，通过队列+消息通信
   - **建议**：对于实时性要求高的（如WiFi）使用中断+DMA

---

## 4. 内存使用优化策略

### 4.1 堆栈总量预算（当前）

```
应用任务堆栈：
  app_power:       8192  
  ambient_out:    10240
  ambient_rx:     10240
  app_light:       4096
  app_rtc:         4096
  app_use_btn:     2048
  rs485_master:    4096
  db:              2048
  ────────────────────
  小计:           44960 B (~44KB)

系统固定栈：
  main_task:       8192 (ESP-IDF)
  ipc_task:        1280 (ESP-IDF)
  timer_task:      3584 (ESP-IDF)
  其他系统栈：    ~10KB
  ────────────────────
  小计:           ~23KB

总计：~67KB 栈内存用于FreeRTOS
```

### 4.2 优化目标

```
优化前：67KB
优化后：50-55KB

具体方案：
  1. app_power:      8KB → 6KB  (节省2KB)
  2. ambient_out:   10KB → 6KB  (节省4KB)
  3. ambient_rx:    10KB → 7KB  (节省3KB)
  4. app_rtc:        4KB → 3KB  (节省1KB)
  ────────────────────────────
  小计节省：10KB
```

---

## 5. 性能指标检测方案

### 5.1 栈溢出检测

```bash
# 使能 CONFIG_FREERTOS_WATCH_TICK_IDLE_LIST
# 或使用 esp_task_wdt_add() 监控

// 代码示例
void check_stack_usage(void) {
    uint32_t free_stack = uxTaskGetStackHighWaterMark(NULL);
    ESP_LOGI(TAG, "Stack HWM: %u bytes", free_stack);
}
```

### 5.2 任务延迟测量

```cpp
// 在任务入口添加时间戳
int64_t task_start = esp_timer_get_time();

// 关键操作前后
int64_t op_start = esp_timer_get_time();
// ... 操作 ...
int64_t op_end = esp_timer_get_time();
ESP_LOGI(TAG, "Operation took %lld us", op_end - op_start);
```

### 5.3 优先级反转检测

```cpp
// 可使用 FreeRTOS 提供的任务统计
#include "freertos/queues.h"
#include "freertos/task.h"

void print_task_stats(void) {
    UBaseType_t task_count = uxTaskGetNumberOfTasks();
    TaskStatus_t *statuses = malloc(task_count * sizeof(TaskStatus_t));
    
    uxTaskGetSystemState(statuses, task_count, NULL);
    
    for(int i = 0; i < task_count; i++) {
        printf("%s\tPriority: %d\tState: %d\tStack: %d\n",
               statuses[i].pcTaskName,
               statuses[i].uxCurrentPriority,
               statuses[i].eCurrentState,
               statuses[i].usStackHighWaterMark);
    }
    free(statuses);
}
```

---

## 6. 推荐优化优先级

### 第一阶段（3天）- 低成本高收益

1. **app_power 栈优化** (8KB → 6KB)
   - 工作量：小
   - 收益：2KB + 潜在流畅度提升
   
2. **频谱分析精度调整**
   - 工作量：小
   - 收益：15-25% CPU释放

3. **NVS异步缓存**
   - 工作量：中
   - 收益：降低UI响应延迟

### 第二阶段（1周）- 中等投入

4. **ambient_rx/out 栈精测**
   - 工作量：中
   - 收益：7KB
   
5. **优先级重新评估与协调**
   - 工作量：中
   - 收益：实时性改善

### 第三阶段（可选）- 高投入

6. **按键中断重构**
   - 工作量：大
   - 收益：10-20% 功耗/CPU

7. **UDP socket 高级配置**
   - 工作量：中
   - 收益：丢包率 ↓，功耗 ↓

---

## 7. 潜在风险与注意事项

| 优化项 | 风险 | 缓解方案 |
|--------|------|---------|
| 减少栈大小 | 栈溢出 | 充分测试+HWM监控 |
| 降低优先级 | 延迟增加 | 实时性测量验证 |
| 异步NVS | 数据不一致 | 添加互斥锁保护 |
| 改按键采样 | 误触发 | 充分消抖验证 |
| FFT精度降低 | 光效不流畅 | A/B对比测试 |

---

## 8. 快速成果清单

```
[ ] 1. 测量 app_power 实际栈用量
    → 目标：确认是否可从8KB降至6KB

[ ] 2. 添加 stack monitor 检测工具
    → 目标：持续监控栈溢出风险

[ ] 3. 频谱分析режим切换
    → 目标：音乐模式使用5分段，测试模式10分段

[ ] 4. ambient_rx/out 栈大小精测
    → 目标：各自消减2-3KB

[ ] 5. 优先级仿真测试
    → 目标：验证倒序优先级是否会导致丢包

[ ] 6. NVS缓存实现
    → 目标：降低平均写入延迟50%

[ ] 7. 按键采样周期评估
    → 目标：是否可从10ms调整到20ms
```

---

**报告日期**：2026-04-15  
**分析工具**：代码审查 + FreeRTOS文档  
**下一步**：实施第一阶段优化，1周内启动
