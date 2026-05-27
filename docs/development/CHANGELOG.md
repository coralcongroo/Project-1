# Changelog

> 说明：本文按时间记录当时发生的改动，条目中的文件路径、目录名和组件归属反映的是“变更发生当时的仓库状态”。
>
> 因此：
> - 历史条目中出现旧路径是正常的，不应直接视为当前路径指引。
> - 查询当前有效目录结构时，请优先参考 `docs/README.md`、`docs/architecture/PROJECT_STRUCTURE.md` 和 `docs/development/BUILD.md`。

## 2026-04-21 — 倒计时任务管理系统 - 三协议集成完成

### BLE 分片协议栈
- 新增 `components/network/bluetooth_protocol_compat/ble_countdown_proto.h/c` (420 行)
- 定义 BEGIN(0x30) / CHUNK(0x31) / COMMIT(0x32) / ABORT(0x33) 帧类型
- 实现 13 种 TLV 编码类型（时间、功率、灯光、色彩）
- 会话管理 (最多 2 个并发，3s 超时自动回收)
- CRC16 校验（多项式 0xA001）

### 协议汇聚与集成
- UDP JSON 命令端口 5569：6 个命令（add/remove/query/list/stats/clear）
- MQTT 主题集成：`iot/device/{MAC}/timer` / `timer_reply`
- 蓝牙集成 (`main/app/app_bluetooth.c` +170 行)：
  - `app_ble_parse_countdown_tlv()` 完整 TLV 解析
  - `app_ble_countdown_commit_cb()` 回调实现
  - 汇聚到统一入口 `app_countdown_add_task()`

### 核心功能完成
- 计时器三类型：ONCE / DAILY / WEEKLY
- 灯光三色彩：CCT / HSI / XY 全参数支持
- 时间精度：1 秒检查循环（±1s 执行偏差）
- 并发支持：最多 16 个任务
- 数据持久化：NVS Flash 存储，重启后自动恢复

### 测试工具与文档
- 新增 `tools/ble_countdown_test.py` (366 行) — BLE 包生成器（自动分片、CRC16）
- 3 份文档完成：IMPLEMENTATION (578L) / INTEGRATION_TEST (433L) / CHECKLIST (249L)
- 代码统计总计：4,050 行（核心库 810 + 协议 420 + 集成 1043 + 工具 517 + 文档 1260）

### 编译验证
- 编译通过：`idf.py build` ✅（0 警告、0 错误）
- 二进制：1,905,536 字节 (40% 分区可用)
- 生产就绪度：90% （待现场设备验证）

---

## 2026-04-21 — Matter 线程安全修复 + 温度保护闭环 + 热参数配置化

### Matter 线程安全与复位流程
- 修复按键长按 3 秒触发配网窗口时的 CHIP lock assert
- `matter_open_commissioning_window()` 与 `matter_schedule_factory_reset()` 改为 `PlatformMgr().ScheduleWork()` 执行
- 工厂复位前新增 WiFi 清理流程：`esp_wifi_disconnect()` / `esp_wifi_stop()` / `esp_wifi_restore()`

### 温度采集与过温联动
- 启用 `app_power_adc_temp_handle()` 温度处理链路，周期写入 `board_temp` / `led_temp` / `over_temp`
- 增加过温滞回逻辑，避免阈值附近频繁抖动
- 新增过温功率联动：过温时下调 `power_limit`，恢复后回到正常上限

### Kconfig 参数化
- 在 `main/Kconfig.projbuild` 新增 Thermal Protection 菜单配置项：
  - `THERMAL_OVER_TEMP_THRESHOLD_C`
  - `THERMAL_RECOVER_TEMP_THRESHOLD_C`
  - `THERMAL_DERATE_POWER_LIMIT_PCT`
  - `THERMAL_NORMAL_POWER_LIMIT_PCT`
- 在 `sdkconfig.defaults` 同步新增默认值（85/78/60/100）

### 构建验证
- 执行 `idf.py reconfigure && idf.py build` 通过
- 固件尺寸: 1,888,368 B (`0x1CD070`), 分区剩余约 40%

## 2026-04-20 — Matter 反向上报 + 按键功能 + 死代码清理

### Matter 属性反向上报
- 新增 `matter_report_state_change()` 回调，注册至 `state_manager`
- 当 BLE/UDP/MQTT 等非 Matter 来源更改灯光状态时，自动同步至 Matter 集群
  - OnOff、LevelControl、ColorControl (CCT/HSI/XY) 全属性覆盖
  - 通过 `PlatformMgr().ScheduleWork()` 保证 Matter 线程安全
  - `MatterReportingAttributeChangeCallback` 通知 HomeKit/Google Home 订阅方
  - 跳过 `STATE_SOURCE_MATTER` 防止反馈回环
- DeviceCallbacks.h 新增函数声明，main.cpp 注册回调

### 按键功能实现
- 单击 (CLICK): 电源开关切换（原有）
- 长按 3s (LONG_START): 打开 Matter 配网窗口 (`OpenBasicCommissioningWindow`)
- 超长按 6s (LONG_HOLD): 触发 Matter 工厂复位 (`ScheduleFactoryReset`)
- 新增 `matter_open_commissioning_window()` 和 `matter_schedule_factory_reset()` (C-linkage)

### 死代码清理
- 删除 `main/boot/` 目录 (5 文件): system_bootstrap.c/h, service_registry.c/h, service_lifecycle.h
- 从 CMakeLists.txt 移除对应 SRCS 和 PRIV_INCLUDE_DIRS
- 这些文件实现了未被调用的"服务注册-批量启动"机制

### 审查结论
- `app_debug` 模块保持现状：工厂调试 UART 接口，生产环境正确禁用

### 固件尺寸
- 当前: 1,884,176 B (0x1CC010), 40% 分区剩余 (3MB 分区)

## 2026-04-20 — 工程结构重构 + Kconfig 配置统一 + 待接入代码集成

### 工程结构重构
- `components/` 按功能分为 8 个子目录: drivers, network, framework, lighting, input, console, utils, app
- 19 个组件 + `modules/`(6 个灯光库) + `utilities/`(crc32, temp_db) 归类整合
- 顶层 `CMakeLists.txt` EXTRA_COMPONENT_DIRS 更新为 8 个路径
- 修复 `local_output` 硬编码 `at/bluetooth_protocol_compat` 路径

### 待接入代码集成 (+5 个源文件)
- `app_power.c` (ADC + FFT 音频分析, 500 行) → `local_output` 组件编译
- `app_use_btn.c` (按键输入处理, 111 行) → `local_output` 组件编译
- `app_debug.c` (UART 调试协议, 148 行) → `local_output` 组件编译
- `boot/system_bootstrap.c` (分阶段启动编排, 114 行) → `main` 组件编译
- `boot/service_registry.c` (服务注册表, 51 行) → `main` 组件编译
- `local_manager.c` 添加 `app_power_init()`, `app_use_init()`, `app_debug_init()` 调用
- `local_output/CMakeLists.txt` 新增 FlexibleButton, esp_adc, espressif__dl_fft 依赖

### Kconfig 配置统一
- `main/Kconfig.projbuild` 扩展为 ~220 行统一菜单，包含 4 个子菜单:
  - Product Profile (8 项): PRODUCT_FUNCTION, LED_TYPE, CCT_MIN/MAX 等
  - Ambient Light Protocol (16 项): WiFi SSID/密码, 组播地址/端口, 灯带 GPIO 等
  - MQTT Agent (12 项): broker URI, TLS 选项, 主题格式等
  - Debug & Features (4 项): BLE 开关, UART 调试引脚
- 删除 `mqtt_agent/Kconfig` (已内联至 main/Kconfig.projbuild)
- `project_config.h` 改用 `#include "sdkconfig.h"` + `#ifndef` 兜底模式
- `app_debug.c` UART 引脚改用 `CONFIG_DEBUG_UART_*` Kconfig 宏
- `sdkconfig.defaults` 新增 Product Profile 和 MQTT Agent 默认值段

### 清理修复
- 删除 4 个空文档: API.md, DEBUGGING.md, MQTT_TOPICS.md, PROTOCOL_SPEC.md
- 修复 `app_debug.c` TAG 拼写错误 (app_qebug → app_debug)
- 移除 `sdkconfig.defaults` 重复的 `CONFIG_ESP_MAIN_TASK_STACK_SIZE=7168`

### 固件尺寸
- 当前: 1,882,400 B (0x1CB920), 40% 分区剩余 (3MB 分区)

## 2026-04-17 — 网络架构优化 + 固件瘦身

### 错误传播机制
- 新增 `NET_EVENT` 自定义事件总线 (`components/common/include/network_event.h`)
- WiFi/MQTT 关键错误通过 `esp_event_post()` 传播到应用层
- 事件类型: `WIFI_CONNECTED`, `WIFI_RECONNECT_FAILED`, `MQTT_CONNECTED/DISCONNECTED/ERROR`
- `main.cpp` 中注册统一处理器 `on_net_event()`

### WiFi 职能归一
- WiFi 连接生命周期统一由 Matter `ConnectivityManager` 管理
- `ambient_wifi.c` 精简为纯 IP 事件观测层（~67 行，原 ~217 行）
  - 移除: `esp_wifi_init/connect`, 独立重连状态机, 指数退避逻辑
  - 移除: `wifi_manager_get_ip_info()` (无调用方)
  - 保留: `ambient_wifi_connected()`, `ambient_wifi_wait_connected()`
- WiFi 省电控制 (`WIFI_PS_NONE`) 移至 `main.cpp::on_ip_event()` 统一管理
- `NET_EVENT_WIFI_CONNECTED` 发布移至 `main.cpp::on_ip_event()`
- `cmd_wifi` 组件移除 `common` 依赖（不再引用 `network_event.h`）

### MQTT 事件传播
- `mqtt_agent.c` 在 CONNECTED/DISCONNECTED/ERROR 时发布 `NET_EVENT`
- 新增公开 API: `mqtt_agent_connected()`

### 目录结构清理
- 删除 `main/cpu0/` 全部 26 个空骨架文件 (ble/mqtt/network/udp/matter/lwm2m)
- 删除 `main/cpu1/` 25 个空占位文件 + output/ 死代码
- 删除 `main/core/` 3 个空占位文件
- 删除 `main/main.c` 旧入口
- 移动 `main/cpu1/local_manager.c/h` → `main/app/local_manager.c/h`
- 更新 `components/local_output/CMakeLists.txt` 源路径

### UDP 修复
- 修复 `ambient_receiver.c` 中 `recvfrom` 缓冲区大小 bug
  - `sizeof(rx_buffer)` → `CONFIG_AMBIENT_MAX_FRAME_SIZE` (4 字节 → 2048 字节)

### 固件瘦身 (累计 -161KB, 8.3%)
- **编译优化**: `-Og` → `-Os` (`CONFIG_COMPILER_OPTIMIZATION_SIZE`)
- **TLS 证书包**: FULL → CMN (`CONFIG_MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_CMN`)
- **Newlib nano printf**: 启用 `CONFIG_NEWLIB_NANO_FORMAT`
- **NimBLE 裁剪**: 禁用 BLE 5.0 扩展扫描/周期同步/Coded PHY
- **Matter SDK 裁剪**:
  - `CONFIG_CHIP_CONFIG_IM_PRETTY_PRINT=n`
  - `CONFIG_ENABLE_TEST_SETUP_PARAMS=n`
  - `CONFIG_TEST_EVENT_TRIGGER_ENABLED=n`
  - `CONFIG_ENABLE_WIFI_TELEMETRY=n`
  - `CONFIG_MAX_FABRICS` 5 → 3
  - 事件日志缓冲减半

### 固件尺寸
- 优化前: 1,956,875 B (1.87MB), 38% 分区剩余
- 优化后: 1,794,928 B (1.71MB), 43% 分区剩余

### 文档
- 重写 `docs/architecture/PROJECT_STRUCTURE.md` 反映实际目录结构
- 更新 `docs/network/NETWORK_MANAGEMENT.md` 反映 WiFi 归一/事件总线
- 更新 `docs/network/NETWORK_ARCHITECTURE_CAPACITY.md` 反映启动时序变更