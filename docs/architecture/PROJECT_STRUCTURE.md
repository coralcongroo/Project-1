# ESP32-S3 智能灯具 — 项目目录结构

> 本文档反映当前实际代码结构。所有列出的文件真实存在且有明确用途。

## 概览

项目采用 ESP-IDF v5.4 组件化架构，核心逻辑拆分为独立 `components/`，
`main/` 仅保留应用入口和设备特有业务代码。

双核分工通过组件内 `xTaskCreatePinnedToCore()` 实现：
- **CPU0**：Matter 主循环 + 网络协议 (WiFi/MQTT/UDP)
- **CPU1**：灯光输出 + 硬件控制 (LED/RS485/PWM)

## 目录树

```
Aputure_IP_Project/
├── CMakeLists.txt                     # 顶层 — 设置 Matter SDK、EXTRA_COMPONENT_DIRS
├── sdkconfig                          # SDK 配置（编译时生成）
├── sdkconfig.defaults                 # 默认配置基线
├── partitions.csv                     # 分区表
│
├── main/                              # 主应用入口 (ESP-IDF main component)
│   ├── CMakeLists.txt                 # 编译: main.cpp, app_rtc.c, stack_monitor.c, DeviceCallbacks.cpp
│   ├── Kconfig.projbuild              # 项目级 Kconfig 选项
│   ├── main.cpp                       # app_main() — Matter 初始化、IP 事件、启动编排
│   ├── DeviceCallbacks.cpp            # Matter 属性回调 (OnOff/Level/Color → state_manager)
│   ├── include/
│   │   └── DeviceCallbacks.h
│   │
│   ├── app/                           # 应用业务模块 (通过 local_output 组件编译)
│   │   ├── local_manager.c/h          # CPU1 任务入口 — 创建灯控/BLE/RS485 子任务
│   │   ├── app_light.c/h              # 灯光状态 → light_control_facade 映射
│   │   ├── app_bluetooth.c/h          # BLE AT 协议桥接 (CONFIG_LOCAL_OUTPUT_ENABLE_BLUETOOTH_APP)
│   │   ├── app_rs485_master.c/h       # RS485 多灯主站通信
│   │   ├── app_local_db.c/h           # 本地存储 (NVS 键值)
│   │   ├── app_rtc.c/h                # RTC/SNTP 时间同步 + 地理位置时区
│   │   ├── app_power.c/h              # ADC 音频采集 + FFT 频谱分析
│   │   ├── app_use_btn.c/h            # 按键输入处理 (开关灯)
│   │   └── app_debug.c/h              # UART 调试命令协议 (待启用)
│   │
│   ├── boot/                          # 启动服务框架 (main 组件编译)
│   │   ├── system_bootstrap.c/h       # 分阶段启动编排
│   │   ├── service_registry.c/h       # 服务注册表
│   │   └── service_lifecycle.h        # 生命周期接口
│   │
│   ├── light/                         # 灯控核心逻辑 (通过 local_output 组件编译)
│   │   ├── light_control_facade.c/h   # 统一灯控入口 — CCT/HSI/XY → dev_lamp
│   │   ├── light_control_bus.c/h      # 多协议灯控总线 (local + RS485)
│   │   └── state_store.c/h            # 灯控状态缓存
│   │
│   ├── proto/                         # 设备协议翻译 (通过 local_output 组件编译)
│   │   ├── point_light_firmware.c/h   # 灯具固件协议适配 (13K 行)
│   │   ├── ble_mesh_protocol.h        # BLE Mesh 协议帧定义
│   │   └── pdt2_protocol.h            # PDT2 协议帧定义
│   │
│   └── utils/
│       └── stack_monitor.c/h          # FreeRTOS 任务栈水位监控
│
├── components/                        # 可复用组件 — 按功能分组
│   │
│   ├── framework/                     # ═══ 核心框架 ═══
│   │   ├── common/                    # 公共工具 + 网络事件定义
│   │   │   ├── include/
│   │   │   │   ├── network_event.h    #   NET_EVENT 事件总线 (WiFi/MQTT 错误传播)
│   │   │   │   ├── common_types.h
│   │   │   │   ├── logger.h
│   │   │   │   ├── ringbuf.h
│   │   │   │   └── crc.h
│   │   │   └── src/
│   │   │       ├── logger.c
│   │   │       └── network_event.c    #   ESP_EVENT_DEFINE_BASE(NET_EVENT)
│   │   │
│   │   ├── state_manager/             # ⭐ 全局状态管理 — 单一真值源 + 版本号
│   │   │   ├── include/
│   │   │   │   ├── state_manager.h    #   get/update/register_callback API
│   │   │   │   └── state_types.h      #   device_state_t, light_mode, state_source_t
│   │   │   └── src/
│   │   │       ├── state_manager.c
│   │   │       ├── state_persistence.c#   NVS 持久化
│   │   │       └── state_history.c    #   变更历史
│   │   │
│   │   ├── ipc_manager/               # ⭐ 核间通信 — FreeRTOS 队列 IPC
│   │   │   ├── include/
│   │   │   │   ├── ipc_queue.h        #   ipc_send / ipc_manager_init
│   │   │   │   ├── ipc_message.h      #   IPC 消息结构
│   │   │   │   └── ipc_types.h        #   目标定义 IPC_TARGET_CPU0/CPU1
│   │   │   └── src/
│   │   │       ├── ipc_manager.c
│   │   │       └── ipc_serializer.c
│   │   │
│   │   └── protocol_dispatcher/       # ⭐ 协议路由 — 多协议同步 + 源跳过
│   │       ├── include/
│   │       │   ├── protocol_dispatcher.h  # dispatch_state / set_online API
│   │       │   └── protocol_types.h   #   MQTT/Matter/UDP/BLE 枚举
│   │       └── src/
│   │           └── protocol_dispatcher.c
│   │
│   ├── drivers/                       # ═══ 硬件驱动 ═══
│   │   ├── dev_lamp/                  # 灯具 HAL — 色彩混合 → PWM/WS28xx
│   │   ├── dev_ws28xx/                # WS2812/APA102 LED 驱动 (SPI)
│   │   ├── dev_touch_slider/          # 触摸滑条驱动 (I2C)
│   │   └── rs485/                     # RS485 UART 驱动 + 多包协议
│   │
│   ├── network/                       # ═══ 网络通信 ═══
│   │   ├── cmd_wifi/                  # WiFi 状态观测 + UDP 组播接收
│   │   │   ├── include/
│   │   │   │   ├── ambient_wifi.h     #   connected / wait_connected (纯状态观测)
│   │   │   │   ├── ambient_receiver.h #   receiver_start
│   │   │   │   ├── ambient_output.h   #   帧输出队列
│   │   │   │   ├── ambient_protocol.h #   AMBL 帧解析
│   │   │   │   └── ambient_config.h   #   组播地址/端口/帧参数
│   │   │   └── *.c
│   │   │
│   │   ├── mqtt_agent/                # MQTT 接入 — TLS 连接 + JSON 状态同步
│   │   │   ├── include/
│   │   │   │   └── mqtt_agent.h       #   init / connected API
│   │   │   ├── src/
│   │   │   │   └── mqtt_agent.c
│   │   │   └── certs/
│   │   │       └── emq_root_ca.pem
│   │   │
│   │   ├── sync_time/                 # SNTP + IP 地理定位时区
│   │   ├── at/                        # BLE AT 命令客户端
│   │   └── bluetooth_protocol_compat/ # BLE Mesh ↔ 灯控协议转换
│   │
│   ├── lighting/                      # ═══ 灯光控制 ═══
│   │   ├── color_mixing/              # 色彩混合算法 (预编译 .a)
│   │   ├── color_mixing_port/         # 色彩混合平台移植
│   │   ├── los_sta_data/              # 灯具状态数据结构
│   │   ├── light_effect/              # 灯效引擎
│   │   ├── light_effect_pixel/        # 像素灯效
│   │   ├── fx_structure_tools/        # FX 结构工具
│   │   └── SidusProFX/                # Sidus Pro 灯效
│   │
│   ├── input/                         # ═══ 用户输入 ═══
│   │   └── FlexibleButton/            # 按键库 (单击/双击/长按)
│   │
│   ├── console/                       # ═══ 调试控制台 ═══
│   │   ├── cmd_nvs/                   # NVS CLI 命令
│   │   └── cmd_system/                # 系统 CLI 命令
│   │
│   ├── utils/                         # ═══ 通用工具 ═══
│   │   ├── crc32/                     # CRC32 算法
│   │   └── temp_db/                   # 温度数据库
│   │
│   └── app/                           # ═══ 应用层 ═══
│       └── local_output/              # CPU1 灯控编排 — 整合 main/app + main/light + main/proto
│           ├── include/
│           │   └── local_output.h     #   init / start_network_services
│           └── src/
│               └── local_output.c
│
├── protocols/                         # 第三方协议 SDK
│   ├── connectedhomeip/              # Matter SDK (CHIP) — GN 子构建
│   └── mqtt/                          # MQTT 库
│
├── tests/                             # 单元测试
├── tools/                             # Python 工具脚本
├── docs/                              # 文档
└── platform/                          # 平台配置 (分区/链接脚本)
```

## 编译路径

### main 组件直接编译 (6 个文件)

| 文件 | 用途 | CPU |
|------|------|-----|
| `main.cpp` | Matter 启动、IP 事件监听、服务编排 | CPU0 |
| `DeviceCallbacks.cpp` | Matter ZCL 属性变更 → state_manager | CPU0 |
| `app/app_rtc.c` | IP 就绪后启动 SNTP/地理时区 | CPU0 |
| `utils/stack_monitor.c` | 后台任务栈水位巡检 | — |
| `boot/system_bootstrap.c` | 分阶段启动编排 (服务注册 → 批量启动) | CPU0 |
| `boot/service_registry.c` | 服务注册表 (启动函数数组管理) | CPU0 |

### local_output 组件间接编译 (main/ 下 12 个文件)

| 文件 | 用途 | CPU |
|------|------|-----|
| `app/local_manager.c` | CPU1 任务入口 | CPU1 |
| `app/app_light.c` | 灯控状态适配 | CPU1 |
| `app/app_local_db.c` | NVS 本地存储 | CPU1 |
| `app/app_rs485_master.c` | RS485 多灯通信 | CPU1 |
| `app/app_bluetooth.c` | BLE AT 桥接 (可选) | CPU1 |
| `app/app_power.c` | ADC 采集 + FFT 音频分析 | CPU1 |
| `app/app_use_btn.c` | 按键输入处理 (开关灯) | CPU1 |
| `app/app_debug.c` | UART 调试协议 (待启用) | CPU1 |
| `light/light_control_facade.c` | 灯控统一入口 | CPU1 |
| `light/light_control_bus.c` | 多路灯控总线 | CPU1 |
| `light/state_store.c` | 灯控状态缓存 | CPU1 |
| `proto/point_light_firmware.c` | 固件协议适配 | CPU1 |