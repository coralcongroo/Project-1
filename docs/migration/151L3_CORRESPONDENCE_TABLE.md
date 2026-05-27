# 151_l3 与 Aputure_IP_Project 对应表

更新时间: 2026-05-20

源工程:
- /home/ats/git-code/151_l3

目标工程:
- /home/ats/standard_code/Aputure_IP_Project

## 1. 使用说明

本表按“151_l3 路径 -> 当前工程路径 -> 备注”整理。

状态说明:
- 直接对应: 基本是一对一迁移，只是目录调整。
- 拆分对应: 151_l3 单文件/单目录能力在当前工程被拆到多个位置。
- 兼容替代: 功能仍在，但落点或架构已经变化。
- 暂无直接对应: 当前工程没有保留同名或等价单点实现。

## 2. 顶层目录对应

| 151_l3 | Aputure_IP_Project | 状态 | 备注 |
|---|---|---|---|
| main/ | main/ + components/app/local_output/ | 拆分对应 | 当前工程把大量原 main 业务文件改为通过 local_output 组件编译 |
| components/ | components/ | 直接对应 | 但当前工程按 drivers/network/console/input/framework/lighting 重新分组 |
| modules/ | components/lighting/ + components/drivers/rs485/ | 拆分对应 | 原 modules 中的灯光与协议能力被并入组件体系 |
| utilities/ | components/utils/ + components/lighting/ + components/network/bluetooth_protocol_compat/ | 拆分对应 | 工具类目录被功能化重组 |
| docs/ | docs/ | 直接对应 | 当前工程文档更完整，含结构说明和迁移记录 |
| managed_components/ | managed_components/ | 直接对应 | 都是 ESP-IDF 管理依赖 |

## 3. main 目录文件对应

| 151_l3 路径 | 当前工程路径 | 状态 | 备注 |
|---|---|---|---|
| main/main.c | main/main.cpp | 兼容替代 | 当前工程启动入口改为 C++，并增加 Matter 启动编排 |
| main/app_light.c | main/app/app_light.c | 直接对应 | 保留同名核心职责 |
| main/app_light.h | main/app/app_light.h | 直接对应 | 保留同名接口 |
| main/app_bluetooth.c | main/app/app_bluetooth.c | 直接对应 | 由 local_output 条件编译接入 |
| main/app_bluetooth.h | main/app/app_bluetooth.h | 直接对应 | 保留同名头文件 |
| main/app_debug.c | main/app/app_debug.c | 直接对应 | 调试口逻辑仍在 |
| main/app_debug.h | main/app/app_debug.h | 直接对应 | 保留同名结构定义 |
| main/app_local_db.c | main/app/app_local_db.c | 直接对应 | 本地参数存储仍沿用 |
| main/app_power.c | main/app/app_power.c | 直接对应 | ADC/FFT 能力仍在 |
| main/app_power.h | main/app/app_power.h | 直接对应 | 同名保留 |
| main/app_rs485_master.c | main/app/app_rs485_master.c | 直接对应 | 当前工程继续承担 RS485 主站、升级、状态轮询 |
| main/app_rs485_master.h | main/app/app_rs485_master.h | 直接对应 | 同名保留 |
| main/app_rs485_slave.c | 暂无直接对应 | 暂无直接对应 | 当前工程没有保留 slave 侧独立实现 |
| main/app_rtc.c | main/app/app_rtc.c | 直接对应 | 时间同步职责保留 |
| main/app_rtc.h | main/app/app_rtc.h | 直接对应 | 同名保留 |
| main/app_use_btn.c | main/app/app_use_btn.c | 直接对应 | 按键功能保留 |
| main/app_use_btn.h | main/app/app_use_btn.h | 直接对应 | 同名保留 |
| main/ble_mesh_protocol.h | main/proto/ble_mesh_protocol.h | 目录迁移 | 协议头移入 proto/ |
| main/point_light_firmware.h | main/proto/point_light_firmware.h + main/proto/point_light_firmware.c | 拆分对应 | 151_l3 把数组和声明放一起，当前工程拆成声明头 + 数据实现 |
| main/stack_monitor.c | main/utils/stack_monitor.c | 目录迁移 | 工具文件移入 utils/ |
| main/stack_monitor.h | main/utils/stack_monitor.h | 目录迁移 | 同上 |
| main/console_settings.c | 暂无直接对应 | 暂无直接对应 | 当前工程未保留该文件 |
| main/console_settings.h | 暂无直接对应 | 暂无直接对应 | 当前工程未保留该文件 |
| main/CMakeLists.txt | main/CMakeLists.txt + components/app/local_output/CMakeLists.txt | 拆分对应 | 当前工程把 CPU1 业务编译归属下沉到 local_output |
| main/Kconfig.projbuild | main/Kconfig.projbuild | 直接对应 | 项目级配置仍在 main |

## 4. 151_l3 components 对应

| 151_l3 路径 | 当前工程路径 | 状态 | 备注 |
|---|---|---|---|
| components/dev_lamp/ | components/drivers/dev_lamp/ | 目录迁移 | 归入 drivers 分类 |
| components/dev_ws28xx/ | components/drivers/dev_ws28xx/ | 目录迁移 | 归入 drivers 分类 |
| components/dev_touch_slider/ | components/drivers/dev_touch_slider/ | 目录迁移 | 归入 drivers 分类 |
| components/rs485/ | components/drivers/rs485/ | 目录迁移 | RS485 驱动与 packer/port 仍在 |
| components/cmd_wifi/ | components/network/cmd_wifi/ | 目录迁移 | 归入 network 分类 |
| components/sync_time/ | components/network/sync_time/ | 目录迁移 | 归入 network 分类 |
| components/at/ | components/network/at/ | 目录迁移 | BLE AT 相关实现归入 network |
| components/color_mixing/ | components/lighting/color_mixing/ | 目录迁移 | 归入 lighting 分类 |
| components/color_mixing_port/ | components/lighting/color_mixing_port/ | 目录迁移 | 归入 lighting 分类 |
| components/FlexibleButton/ | components/input/FlexibleButton/ | 目录迁移 | 归入 input 分类 |
| components/cmd_nvs/ | components/console/cmd_nvs/ | 目录迁移 | 归入 console 分类 |
| components/cmd_system/ | components/console/cmd_system/ | 目录迁移 | 归入 console 分类 |

## 5. 151_l3 modules 对应

| 151_l3 路径 | 当前工程路径 | 状态 | 备注 |
|---|---|---|---|
| modules/SidusProFX/ | components/lighting/SidusProFX/ | 目录迁移 | 专业灯效引擎保留 |
| modules/fx/ | components/lighting/fx/ | 目录迁移 | 已在当前工程新增并接入 |
| modules/light_effect/ | components/lighting/light_effect/ | 目录迁移 | 传统系统光效保留 |
| modules/light_effect_pixel/ | components/lighting/light_effect_pixel/ | 目录迁移 | 像素光效保留并扩展 |
| modules/los_sta_data/ | components/lighting/los_sta_data/ | 目录迁移 | 核心 light_ctrl / 状态定义保留 |
| modules/rs485/ | components/drivers/rs485/ | 兼容替代 | 当前工程把协议与驱动统一归入 drivers/rs485 |

## 6. 151_l3 utilities 对应

| 151_l3 路径 | 当前工程路径 | 状态 | 备注 |
|---|---|---|---|
| utilities/crc32/ | components/utils/crc32/ | 目录迁移 | 校验工具保留 |
| utilities/temp_db/ | components/utils/temp_db/ | 目录迁移 | 温度库保留 |
| utilities/fx_structure_tools/ | components/lighting/fx_structure_tools/ | 目录迁移 | 归入 lighting 分类 |
| utilities/protocol/ble_protocol_tool.c | components/network/bluetooth_protocol_compat/ble_protocol_tool.c | 目录迁移 | BLE 协议工具移入兼容层 |
| utilities/protocol/trans_ble_mesh_and_light_ctrl.c | components/network/bluetooth_protocol_compat/trans_ble_mesh_and_light_ctrl.c | 目录迁移 | BLE Mesh 与 light_ctrl 转换逻辑移入兼容层 |
| utilities/protocol/include/ | components/network/bluetooth_protocol_compat/include/ | 目录迁移 | 协议转换头文件集中到 bluetooth_protocol_compat |

## 7. 关键一对多拆分映射

| 151_l3 路径 | 当前工程拆分落点 | 备注 |
|---|---|---|
| main/main.c | main/main.cpp；main/DeviceCallbacks.cpp；main/app/local_manager.c | 启动、Matter 属性回调、CPU1 本地任务入口被拆开 |
| main/point_light_firmware.h | main/proto/point_light_firmware.h；main/proto/point_light_firmware.c | 当前工程把声明与大数组实现拆分，便于管理 |
| 151_l3 原 main 业务编译归属 | main/app/*；main/light/*；main/proto/*；components/app/local_output/CMakeLists.txt | 当前工程不再把所有业务都挂在 main 组件上 |
| 151_l3 协议转换散落于 utilities/modules | components/network/bluetooth_protocol_compat/；components/framework/protocol_dispatcher/；main/proto/ | 当前工程把“协议转换”“协议分发”“协议定义”拆成三层 |

## 8. 当前工程新增、151_l3 无直接来源的核心模块

这些不是 151_l3 的一一迁移结果，而是当前工程重构新增的骨架层：

| 当前工程路径 | 作用 |
|---|---|
| components/framework/state_manager/ | 全局状态单一真值源 |
| components/framework/ipc_manager/ | 核间 IPC |
| components/framework/protocol_dispatcher/ | 多协议同步分发 |
| components/app/local_output/ | CPU1 编译收口层 |
| main/light/light_control_bus.c | 灯控总线 |
| main/light/light_control_facade.c | 灯控门面层 |
| main/DeviceCallbacks.cpp | Matter 属性桥接 |

## 9. 快速结论

可以把当前工程理解成：

- 151_l3 的硬件驱动、灯光算法、光效模块，大部分都还能在当前工程找到明确落点。
- 变化最大的不是底层能力，而是“业务编排方式”。
- 当前工程把 151_l3 的平铺式 main/components/modules/utilities 结构，重构成了 drivers/network/lighting/framework/app 的分层组件体系。

如果后续需要继续做文件级迁移，建议优先按本表从下往上查：

1. 先找对应组件目录
2. 再看是直接对应还是拆分对应
3. 遇到拆分对应，优先保留当前工程 framework/light 总线结构，不要整文件覆盖

## 10. 迁移状态矩阵

状态说明:
- 已完成: 当前工程已有明确落点，且迁移文档已确认落地。
- 部分迁移: 已有落点，但只吸收了部分能力，或仍依赖当前工程新架构。
- 未迁移: 还没有对等落点或没有完成实际迁移。
- 不建议迁移: 当前工程已有更高层替代，不建议再按 151_l3 原样搬运。

补充口径（2026-05-22）:

- 若目标改为“完整保留 151_l3 的所有功能，再在此基础上继续开发”，则本表中此前标为“不建议迁移”的项，只有在当前仓库确实已有等价功能承接时才能继续维持原判。
- 若当前仓库没有等价入口或兼容模式，则应重新视为“未迁移的兼容缺口”，而不是默认跳过。

### 10.1 顶层与主链路

| 151_l3 路径 | 当前工程路径 | 迁移状态 | 备注 |
|---|---|---|---|
| main/main.c | main/main.cpp | 部分迁移 | 启动职责已承接，但已重构为 Matter + 服务编排入口 |
| main/app_light.c | main/app/app_light.c | 部分迁移 | 兼容接口已补齐，但内部走 light_control_bus / facade，不再等同原实现 |
| main/app_rs485_master.c | main/app/app_rs485_master.c | 部分迁移 | 已完成低风险对齐，且继续承接当前工程的 RS485/Matter 桥接增强 |
| main/app_rs485_slave.c | 暂无直接对应 | 未迁移 | 在“完整保留 151 功能”目标下，这一项应视为兼容缺口；建议后续以可选 local_output 编译单元方式恢复 |
| main/point_light_firmware.h | main/proto/point_light_firmware.h + main/proto/point_light_firmware.c | 已完成 | 2026-05-20 已同步 151_l3 `5f33117` 的最新点光源固件正文，当前升级入口继续复用现有 `point_light_firmware[] + point_light_firmware_size` |
| main/console_settings.c/h | 暂无直接对应 | 未迁移 | 当前工程未保留该调试设置文件 |

### 10.2 components 层

| 151_l3 路径 | 当前工程路径 | 迁移状态 | 备注 |
|---|---|---|---|
| components/dev_lamp/ | components/drivers/dev_lamp/ | 已完成 | Phase B 已确认 pixel_fx_player 等核心改动落地 |
| components/dev_ws28xx/ | components/drivers/dev_ws28xx/ | 已完成 | 驱动已存在并参与当前灯控链 |
| components/dev_touch_slider/ | components/drivers/dev_touch_slider/ | 已完成 | 目录迁移完成 |
| components/rs485/ | components/drivers/rs485/ | 已完成 | 驱动、packer、port 均已存在并扩展用于当前工程 |
| components/cmd_wifi/ | components/network/cmd_wifi/ | 已完成 | 目录迁移完成，功能继续使用 |
| components/sync_time/ | components/network/sync_time/ | 已完成 | 时间同步组件已存在 |
| components/at/ | components/network/at/ | 已完成 | BLE AT 相关功能已迁移 |
| components/color_mixing/ | components/lighting/color_mixing/ | 已完成 | 颜色混合链已存在 |
| components/color_mixing_port/ | components/lighting/color_mixing_port/ | 已完成 | 平台适配层已存在 |
| components/FlexibleButton/ | components/input/FlexibleButton/ | 已完成 | 按键库已迁移 |
| components/cmd_nvs/ | components/console/cmd_nvs/ | 已完成 | 控制台命令已迁移 |
| components/cmd_system/ | components/console/cmd_system/ | 已完成 | 控制台命令已迁移 |

### 10.3 modules 层

| 151_l3 路径 | 当前工程路径 | 迁移状态 | 备注 |
|---|---|---|---|
| modules/SidusProFX/ | components/lighting/SidusProFX/ | 已完成 | 专业光效引擎已存在 |
| modules/fx/ | components/lighting/fx/ | 已完成 | Phase A 已新增并接入 |
| modules/light_effect/ | components/lighting/light_effect/ | 已完成 | 系统光效目录已存在 |
| modules/light_effect_pixel/ | components/lighting/light_effect_pixel/ | 已完成 | light_effect_pixel_1 等关键文件已补齐 |
| modules/los_sta_data/ | components/lighting/los_sta_data/ | 已完成 | 关键灯控数据结构沿用 |
| modules/rs485/ | components/drivers/rs485/ | 部分迁移 | 驱动与协议已承接，但当前工程进一步并入驱动层与桥接逻辑 |

### 10.4 utilities 层

| 151_l3 路径 | 当前工程路径 | 迁移状态 | 备注 |
|---|---|---|---|
| utilities/crc32/ | components/utils/crc32/ | 已完成 | 工具组件已迁移 |
| utilities/temp_db/ | components/utils/temp_db/ | 已完成 | 工具组件已迁移 |
| utilities/fx_structure_tools/ | components/lighting/fx_structure_tools/ | 已完成 | Phase A 已确认更新 |
| utilities/protocol/ble_protocol_tool.c | components/network/bluetooth_protocol_compat/ble_protocol_tool.c | 已完成 | 已迁移到兼容层 |
| utilities/protocol/trans_ble_mesh_and_light_ctrl.c | components/network/bluetooth_protocol_compat/trans_ble_mesh_and_light_ctrl.c | 已完成 | 已迁移到兼容层 |
| utilities/protocol/include/ | components/network/bluetooth_protocol_compat/include/ | 已完成 | 对应头文件已集中迁移 |

### 10.5 当前工程新增骨架层

这些能力不是从 151_l3 逐文件迁移过来的，因此不应反向要求做一一对齐。

| 当前工程路径 | 与 151_l3 的关系 | 建议 |
|---|---|---|
| components/framework/state_manager/ | 151_l3 无同级骨架 | 不建议回退到 151_l3 写法 |
| components/framework/ipc_manager/ | 151_l3 无同级骨架 | 不建议回退到 151_l3 写法 |
| components/framework/protocol_dispatcher/ | 151_l3 协议分发职责被拆散在多处 | 不建议按原 main/modules 结构覆盖 |
| components/app/local_output/ | 151_l3 无同级编译收口层 | 不建议迁移掉 |
| main/light/light_control_bus.c | 151_l3 无同级总线层 | 不建议迁移掉 |
| main/light/light_control_facade.c | 151_l3 无同级门面层 | 不建议迁移掉 |
| main/DeviceCallbacks.cpp | 151_l3 无 Matter 层 | 不建议迁移掉 |

## 11. 建议的后续用法

如果你要继续做逐项清理或迁移，建议直接以本节状态矩阵为准：

1. 优先看“部分迁移”项，这些最容易形成行为偏差。
2. “未迁移”项先判断是否仍有业务需求，再决定要不要补。
3. “不建议迁移”项默认保持当前工程架构，不要为了对齐而回退。

## 12. 功能点级差异表

这一节只展开当前最值得继续追的三项：

- main/app/app_light.c
- main/app/app_rs485_master.c
- components/drivers/rs485/

### 12.1 main/app_light.c

| 功能点 | 151_l3 | 当前工程 | 判断 |
|---|---|---|---|
| 对外入口名 | `app_light_send_msg()`、`app_light_prepare_power_on_ctrl()` | 同名接口保留 | 已对齐 |
| 上电恢复 light_ctrl | 直接读写 `temp_db`，并在 app_light 内处理 | 改为 `light_control_prepare_power_on()` 封装 | 兼容替代 |
| 命令入队模型 | 信号量唤醒 + 直接读 `light_ctrl` | `light_control_bus_publish_command()` + 本地队列 | 架构重构 |
| 应用前预处理 | 在 app_light 内完成 partition cache / force all on / DB 同步 | 改为 `light_control_prepare_for_apply()` / `light_control_note_current_ctrl()` / `state_store_*()` | 拆分迁移 |
| 实际下灯 | `lamp_set_pixel()` | 仍是 `lamp_set_pixel()` | 已对齐 |
| 电源状态判断 | 直接查 DB | 改为 `state_store_get_power_on()` | 兼容替代 |
| 事件回传 | 无统一总线事件语义 | 新增 `light_control_bus_publish_event()` | 当前工程新增 |

结论:

- `app_light.c` 的“接口层职责”基本还在。
- 151_l3 中原本塞在单文件里的 DB、分区模式缓存、队列调度，已经被拆到 `state_store`、`light_control_bus`、`light_control_facade` 等层。
- 这部分不建议再按 151_l3 原文件整段回贴；后续如果补行为，应优先补到 facade/bus/state_store，而不是把旧逻辑塞回 app_light。

### 12.2 main/app_rs485_master.c

| 功能点 | 151_l3 | 当前工程 | 判断 |
|---|---|---|---|
| RS485 主站任务、事件队列 | 有 | 有 | 已对齐 |
| 开机探测版本并按固件头比对升级 | 有 | 有 | 已对齐 |
| 固件升级传输流程 | Start -> Size -> Data -> CRC | 同流程保留 | 已对齐 |
| 内置固件来源 | `point_light_firmware[]` | `point_light_firmware[] + point_light_firmware_size` | 已对齐 |
| 首次连上后同步开关与灯态 | 有 | 仍保留，但启动后不再把逻辑散在 DB 路径里 | 兼容替代 |
| `LIGHT_MODE_CCT`/`HSI` 下发 | 有 | 有 | 已对齐 |
| `LIGHT_MODE_PWM` 下发 | legacy 主站文件已存在 `Factory_RGBWW` 发送函数，但 `LIGHT_MODE_PWM` 实际仍归到 HSI 分支 | 已改为 `Factory_RGBWW` 并走统一映射 | 当前工程增强 |
| `LIGHT_MODE_XY` 下发 | 151_l3 全仓存在 XY 模式，但 `app_rs485_master.c` 内未见 XY 相关 RS485 下发 | 新增 `Color_Mixing XY` 下发 | 当前工程增强 |
| 状态轮询 | 主要查版本/温度 | 扩展到 `Switch + Factory_RGBWW + Temperature` | 当前工程增强 |
| 重连后按当前状态回灌从机 | 断线恢复后会先同步当前开关与灯态 | 已改为从 `state_store` 读取当前 power/light_ctrl，并在首次连通或重连后回灌 | 2026-05-19 已补齐 |
| 从机主动上报入口 | 无公共统一入口 | 新增 `app_rs485_master_handle_rx_frame()` | 当前工程增强 |
| 入站状态回写 Matter | 无 | 新增 `matter_sync_rs485_snapshot()` | 当前工程新增 |
| 线程等待模型 | 常驻阻塞等队列 | 改为短超时等事件 + 空闲收 UART | 当前工程增强 |

结论:

- `app_rs485_master.c` 不是“未迁完”，而是“在 151_l3 基础上继续承担了当前工程新增职责”。
- 真正需要继续补对齐的，不是旧版发送/升级主流程，这些已经基本齐了；而是要继续核查 151_l3 是否还有某些边缘查询命令、异常处理、回调语义没被吸收。
- 其中 `9ed22c0` 提交里的“重连后回灌当前状态”子行为已经在 2026-05-19 按当前架构补齐，落点仍保持在 `main/app/app_rs485_master.c + state_store`，没有回退到 legacy `temp_db` 直读写法。
- 后续若继续深挖，最值得拆的是“命令覆盖矩阵”和“异常恢复矩阵”。

#### 12.2.1 命令覆盖矩阵

下表只统计 `app_rs485_master.c` 实际发送、查询、解析过的命令，不等于整个 RS485 协议全集。

| 协议命令 | 枚举值 | 151_l3 使用情况 | 当前工程使用情况 | 覆盖判断 | 备注 |
|---|---|---|---|---|---|
| Version | `RS485_Cmd_Version` | 启动阶段读版本，决定是否升级 | 同样在启动阶段读取版本，并维持连通性判断 | 已对齐 | 当前工程仍以固件头版本比对为升级入口 |
| HSI | `RS485_Cmd_HSI` | `LIGHT_MODE_HSI` 写下发 | `LIGHT_MODE_HSI` 写下发 | 已对齐 | 报文结构未变 |
| CCT | `RS485_Cmd_CCT` | `LIGHT_MODE_CCT` 写下发 | `LIGHT_MODE_CCT` 写下发 | 已对齐 | 报文结构未变 |
| Sys_FX | `RS485_Cmd_Sys_FX` | 系统光效写下发 | 系统光效写下发 | 已对齐 | 仍通过 `light_ctrl_to_rs485_fx()` 投影 |
| Switch | `RS485_Cmd_Switch` | 启动同步与电源事件写下发 | 保留写下发，并新增状态查询与主动上报解析 | 增强覆盖 | 当前工程同时覆盖写、读、入站解析三条路径 |
| Temperature_Msg | `RS485_Cmd_Temperature_Msg` | 周期查询温度 | 保留周期查询温度 | 已对齐 | 当前仍作为连通性参考之一 |
| FileTransfer | `RS485_Cmd_FileTransfer` | 固件升级写传输 | 固件升级写传输 | 已对齐 | `Start -> Size -> Data -> CRC` 流程保持一致 |
| Factory_RGBWW | `RS485_Cmd_Factory_RGBWW` | legacy 主站文件里已有发送函数与命令名映射，但 `LIGHT_MODE_PWM` 分支未真正走到这里；另在 `app_rs485_slave.c` 可见接收处理 | `LIGHT_MODE_PWM` 写下发，同时支持读查询和主动上报解析 | 当前工程增强 | 当前工程把“存在命令”推进成“真正主路径 + 查询 + 入站解析” |
| Color_Mixing | `RS485_Cmd_Color_Mixing` | 未见使用 | `LIGHT_MODE_XY` 走写下发 | 当前工程新增 | 当前工程用它承接 XY 控制，而不是直接走 `XY_Coordinate` |

#### 12.2.1.1 跨文件补充结论：LIGHT_MODE_XY

围绕当前编辑点 `LIGHT_MODE_XY`，补一条更准确的仓级结论：

| 观察点 | 151_l3 | 当前工程 | 结论 |
|---|---|---|---|
| XY 模式是否存在于状态/协议转换层 | 存在：`app_local_db`、`trans_ble_mesh_and_light_ctrl`、`los_light.h`、`dev_lamp.c` 都能看到 `LIGHT_MODE_XY` | 同样存在，并贯通 `trans_ble_mesh_and_light_ctrl`、`DeviceCallbacks.cpp`、`state_manager`、`dev_lamp.c` | 两边都支持 XY 作为颜色模式语义 |
| XY 是否由 `app_rs485_master.c` 直接下发到 RS485 | 未见 `LIGHT_MODE_XY`、`XY_Coordinate`、`Color_Mixing` 在 151_l3 的 `main/app_rs485_master.c` 中出现 | 当前 `main/app/app_rs485_master.c` 有明确 `case LIGHT_MODE_XY`，并发送 `RS485_Cmd_Color_Mixing` | 当前工程把 XY 真正接进了 RS485 主站 |
| XY 走哪条 RS485 命令 | 无证据表明 legacy 主站已覆盖 | 当前走 `RS485_Cmd_Color_Mixing`，而不是 `RS485_Cmd_XY_Coordinate` | 这是当前工程的设计选择，不应误记为“漏迁 XY_Coordinate” |

补充判断:

- 151_l3 的 `LIGHT_MODE_XY` 更像“上层状态与本地灯效语义存在”，而不是“已经打通到 RS485 主站发送面”。
- 当前工程则把这条链补齐了：蓝牙协议转换/状态管理/Matter 状态投影都能保留 XY，最终在 `app_rs485_master.c` 中落到 `RS485_Cmd_Color_Mixing`。
- 因此文档里出现 `LIGHT_MODE_XY` 时，最准确的说法是“当前工程新增了 XY 到 RS485 的完整出口”，而不是“简单沿用了 151_l3 的 XY 发送实现”。

#### 12.2.2 入站解析覆盖

| 入站命令 | 151_l3 | 当前工程 | 判断 | 备注 |
|---|---|---|---|---|
| `RS485_Cmd_Switch` | 无统一公共解析入口 | `app_rs485_master_handle_rx_frame()` 解析并投递 Matter | 当前工程新增 | 为 Endpoint 2 回写准备 |
| `RS485_Cmd_Factory_RGBWW` | 无统一公共解析入口 | `app_rs485_master_handle_rx_frame()` 解析并投递 Matter | 当前工程新增 | 与统一 PWM 映射层对接 |

#### 12.2.3 不应误判为“未迁移”的命令

下面这些命令虽然在协议枚举里存在，但当前没有证据表明 151_l3 的 `app_rs485_master.c` 已经实际承担它们，因此不应直接算成当前工程的迁移缺口：

| 协议命令 | 枚举值 | 当前判断 |
|---|---|---|
| GEL | `RS485_Cmd_GEL` | 不在该文件已知职责范围 |
| RGB | `RS485_Cmd_RGB` | 不在该文件已知职责范围 |
| XY_Coordinate | `RS485_Cmd_XY_Coordinate` | 当前工程改走 `Color_Mixing`，不等于缺失 |
| Dim_Frq | `RS485_Cmd_Dim_Frq` | 未见 151_l3 主站文件实际覆盖 |
| Dimming_Curve / Fan / Power_Suppy / Battery_State | 对应枚举存在 | 需要结合更大范围业务文件再判断，不应先记到本表缺口里 |
| Sys_FX_II / RGBWW / PixelEffect / Partition_* 等扩展命令 | 对应枚举存在 | 更像协议全集能力，不代表该主站文件必须全覆盖 |

补充判断:

- 如果后面继续追“还缺什么命令”，应先区分“协议定义存在”与“151_l3 的主站实现实际使用过”这两件事。
- 就当前证据看，`app_rs485_master.c` 的核心控制面已经从 151_l3 的 `Version/CCT/HSI/Sys_FX/Switch/Temperature/FileTransfer` 扩展到 `Factory_RGBWW/Color_Mixing/主动上报解析/Matter 回写`。
- 因此它更准确的标签不是“部分迁移未完成”，而是“基础能力已迁完，并在当前工程承担了额外桥接职责”。

#### 12.2.4 扩展命令的跨文件使用面

这部分用于回答一个更具体的问题：有些扩展命令并不是“当前工程漏迁”，而是 151_l3 本来也没有把它们落到 `app_rs485_master.c` 这条主站主路径里。

| 命令 / 语义 | 151_l3 中的真实落点 | 当前工程中的真实落点 | 结论 |
|---|---|---|---|
| Factory_RGBWW | `main/app_rs485_master.c` 内有发送函数与命令映射；`main/app_rs485_slave.c` 有接收处理；`main/app_debug.c` 有调试口；但 legacy 主站的 `LIGHT_MODE_PWM` 仍走 HSI 分支 | `main/app/app_rs485_master.c` 成为 PWM 主下发、状态查询、主动上报解析统一入口 | 当前工程把 legacy 的“半接入状态”补成了完整主路径 |
| RGBWW 模式语义 | `app_local_db.c`、`los_light.h`、`trans_ble_mesh_and_light_ctrl.c`、`app_bluetooth.c`、`app_debug.c` 可见 | 当前工程继续保留在状态/协议转换层，但 RS485 主站主出口仍以 `Factory_RGBWW` 为主 | 更像模式语义和协议转换能力，不等于 legacy 主站已覆盖 RS485 `RS485_Cmd_RGBWW` |
| PixelEffect / Partition_Color / Partition_Effect | 在 `rs485_protocol.h` 与协议文档里定义明显，但本次检索未见 legacy 主站业务文件实际 pack/send/parse | 当前工程也未见这些命令进入主站主路径 | 现阶段应视为协议保留能力，不应记为当前工程迁移缺口 |
| GEL / RGB / Fan / Power_Suppy / Battery_State / Sys_FX_II | 主要在协议头和 RS485 模块设计文档中出现；本次未见 151_l3 主站业务文件形成明确调用闭环 | 当前工程同样主要停留在协议定义层 | 这些更像协议全集能力，是否需要迁要看其他业务文件，而不是只看主站文件 |

补充判断:

- 这次全仓扫描后，可以把“协议里有这个命令”与“151_l3 的业务主链真的用了这个命令”明确分开。
- 对 `Factory_RGBWW`，当前工程不是从 0 做起，而是把 legacy 中已经露头但没有走通的能力补成了真正主路径。
- 对 `PixelEffect / Partition_* / RGBWW` 这类项，当前更合理的状态不是“待补迁移”，而是“协议已预留，但未见 legacy 主站形成成熟业务闭环”。

### 12.3 components/drivers/rs485/

| 功能点 | 151_l3 | 当前工程 | 判断 |
|---|---|---|---|
| driver / packer / port 三层结构 | 有 | 有 | 已对齐 |
| `rs485_driver_send_recv()` 同步请求-响应 | 有 | 有 | 已对齐 |
| `rs485_driver_recv()` 独立接收入口 | 有 | 有 | 已对齐 |
| packer 头解析、命令解析 | 有 | 有 | 已对齐 |
| 主站空闲收包支持 | 未形成上层闭环 | 已被 `app_rs485_master_handle_rx_frame()` 消费 | 当前工程增强 |
| UART 读首包后补齐整帧 | 旧工程未见针对 `msg_size` 的补齐处理 | 当前 `port_recv()` 已按 `msg_size` 补读尾包 | 当前工程增强 |
| 主动上报转状态同步 | 无 Matter 目标 | 已与 Endpoint 2 回写桥打通 | 当前工程新增 |

结论:

- `components/drivers/rs485/` 目录本身已经迁完，但“怎么被上层消费”发生了明显增强。
- 所以第 10 章里把 `components/rs485 -> components/drivers/rs485` 记成“已完成”没有问题；如果要更精细，可以理解为“目录迁移已完成，运行时消费语义已增强”。

### 12.4 下一步最值得继续拆的项

如果要把这张表继续变成可执行迁移清单，建议按下面顺序继续：

1. 给 `main/app/app_rs485_master.c` 单独做“命令覆盖矩阵”，逐个列出 `Version / Switch / Temperature / Factory_RGBWW / Color_Mixing / FileTransfer / Sys_FX` 是否完全对齐。
2. 给 `main/app/app_light.c` 单独做“状态流转图”，把 `app_light -> light_control_bus -> facade -> lamp_set_pixel` 和 151_l3 的单文件流转并排画出来。
3. 给 `components/drivers/rs485/port/rs485_port_esp.c` 单独补一个“主动上报收包时序”，方便后面做实机联调。