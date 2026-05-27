# 151_l3 底层灯光控制移植计划

更新时间: 2026-05-20
目标分支: test_v_26_04_28
对比源:
- 源工程: /home/ats/git-code/151_l3
- 目标工程: /home/ats/standard_code/Aputure_IP_Project

## 1. 结论摘要

151_l3 最新提交 `ad08ac0` 主要是像素光效引擎（fx/player）能力增强，变更体量较大（26 文件，约 4569 行新增）。

目标工程已经完成架构重构（`state_manager + light_control_bus + light_control_facade + local_output`），与 151_l3 的调用模型不同。

建议策略:
- 保留目标工程现有灯控总线架构
- 定向移植 151_l3 的“效果实现能力”
- 避免直接覆盖 `main` 层控制链

## 2. 本次待迁移变更（151_l3）

来自 `git show --name-only ad08ac0` 的核心文件：

- components/dev_lamp/dev_lamp.c
- main/app_light.c
- main/app_rs485_master.c
- modules/fx/*
- modules/light_effect_pixel/include/light_effect_pixel_1.h
- modules/light_effect_pixel/light_effect_pixel_1.c
- modules/light_effect_pixel/light_effect_pixel.c
- modules/los_sta_data/include/los_light.h
- utilities/fx_structure_tools/trans_light_ctrl_to_fx_legacy.c

## 3. 目标工程对应映射

- `components/dev_lamp/dev_lamp.c`
  -> `components/drivers/dev_lamp/dev_lamp.c`
- `main/app_light.c`
  -> `main/app/app_light.c`
- `main/app_rs485_master.c`
  -> `main/app/app_rs485_master.c`
- `modules/light_effect_pixel/*`
  -> `components/lighting/light_effect_pixel/*`
- `utilities/fx_structure_tools/*`
  -> `components/lighting/fx_structure_tools/*`
- `modules/los_sta_data/include/los_light.h`
  -> `components/lighting/los_sta_data/include/los_light.h`

说明:
- 目标工程不存在 `modules/fx`，建议新建 `components/lighting/fx/` 承接。

## 4. 风险分级

低风险（可先做）:
- 新增 `components/lighting/fx/*`
- 增量补充 `components/lighting/light_effect_pixel/*`
- 更新 `components/lighting/fx_structure_tools/trans_light_ctrl_to_fx_legacy.c`

中风险（需联调）:
- `components/drivers/dev_lamp/dev_lamp.c`
  - 涉及 1ms 回调、pixel_effect 执行路径、PWM 输出

高风险（最后做）:
- `main/app/app_light.c`
- `main/app/app_rs485_master.c`
  - 容易破坏现有 `light_control_bus` 事件链与状态同步闭环

## 5. 分阶段执行计划

### Phase A: 先迁能力模块，不改主链

目标:
- 把 151_l3 新 fx 能力接入目标工程，但不触碰 `app_light/app_rs485_master` 主流程。

动作:
1. 新建组件目录 `components/lighting/fx/`，迁入 `modules/fx` 源码与头文件
2. 更新 `components/lighting/light_effect_pixel` 的新增头/实现
3. 更新 `components/lighting/fx_structure_tools/trans_light_ctrl_to_fx_legacy.c`
4. 更新相应 `CMakeLists.txt` 的 `REQUIRES`

验收:
- `idf.py build` 通过
- 不改控制命令情况下，原有灯光控制行为不退化

### Phase B: 驱动层择优吸收

目标:
- 吸收 `dev_lamp.c` 中与 fx 引擎相关的必要逻辑
- 避免覆盖目标工程中已适配的任务/总线逻辑

动作:
1. 仅移植与 `pixel_effect_init/pixel_effect_task`、`SidusProFX` 相关差异
2. 保留目标工程当前已验证的定时器策略与总线事件发布逻辑
3. 对 RGB/CCT/HSI/XY 输出路径做回归

验收:
- `idf.py build`
- 运行测试:
  - 开关/亮度/CCT/HSI/XY 控制正常
  - 像素特效可启动/停止

### Phase C: 控制层对齐（可选，最后）

目标:
- 若确实需要，局部吸收 `app_light` / `app_rs485_master` 优化点
- 但不能破坏当前 `state_manager -> local_output -> light_control_bus` 闭环

动作:
1. 逐段移植（不要整文件替换）
2. 关键接口保持不变:
   - `light_control_bus_register_command_handler`
   - `light_control_bus_publish_event`
   - `state_manager_update_state`

验收:
- MQTT/Matter/UDP/BLE 输入路径一致
- 倒计时执行路径一致
- RS485 控制与状态查询正常

## 6. 必测清单（每阶段执行）

1. 编译
- `idf.py build`

2. 本地控制
- 按键开关
- 亮度变化
- 色温/色彩切换

3. 网络控制
- MQTT 下发 -> 灯响应 -> 状态回报
- UDP 下发 -> 灯响应

4. 特效
- 进入像素光效
- 退出像素光效
- 与普通模式切换不残留状态

5. RS485
- 主站线程正常
- 温度/版本查询正常
- 下发灯控命令无阻塞

## 7. 不建议做法

- 不建议直接覆盖 `main/app/app_light.c` 和 `main/app/app_rs485_master.c`
- 不建议一次性替换 `dev_lamp.c` 全文件
- 不建议跳过阶段化回归直接上板

## 8. 当前进展（已完成）

### 已完成：Phase A

- [x] 新增 `components/lighting/fx/`，迁入 `fx_engine/fx_effects/fx_player` 核心实现
- [x] 新增 `components/lighting/light_effect_pixel/include/light_effect_pixel_1.h`
- [x] 新增 `components/lighting/light_effect_pixel/light_effect_pixel_1.c`
- [x] 更新 `components/lighting/light_effect_pixel/include/light_effect_pixel.h`（补充 partition mode 字段）
- [x] 更新 `components/lighting/light_effect_pixel/CMakeLists.txt`（增加 `REQUIRES ... fx`）
- [x] 更新 `components/lighting/fx_structure_tools/trans_light_ctrl_to_fx_legacy.c`
- [x] 构建验证通过（`idf.py build`）

### 已完成：Phase B（代码侧）

- [x] 在 `components/drivers/dev_lamp/dev_lamp.c` 接入 `pixel_fx_player`（优先新引擎）
- [x] 保留 legacy `pixel_effect` 回退路径（加载失败自动回落）
- [x] 模式切换时增加 `pixel_fx_player_disable/reset`，避免残留状态
- [x] 增加像素效果参数归一化（速度/颜色数量/partition mode 边界）
- [x] 增加可观测性：新引擎加载成功/失败计数、回退计数、最近失败 rc/mode 记录
- [x] 增加周期状态日志（30s）用于上板联调时快速判读路径命中情况
- [x] 构建验证通过（`idf.py build`）

## 9. 下一步建议（立即可执行）

建议继续执行 Phase B（上板验证闭环）：
- 对 `dev_lamp` 做上板联调验证（普通模式/像素模式切换、退出像素后恢复）
- 观察周期日志中的 `ok/fail/fallback` 统计是否符合预期
- 若稳定，再评估是否进入 Phase C（`app_light/app_rs485_master` 的局部吸收）

## 10. Phase C 启动进展（2026-04-28）

### 已完成：Phase C 第 1 步（兼容接口补齐）

- [x] 在 `main/app/app_light.c` 增加 `app_light_send_msg()` 兼容接口
- [x] 在 `main/app/app_light.c` 增加 `app_light_prepare_power_on_ctrl()` 兼容接口
- [x] 两个接口内部复用 `light_control_bus` / `light_control_facade`，不绕开现有总线闭环
- [x] 在 `main/app/app_rs485_master.c` 增加显式 `los_data.h` 依赖（与 151_l3 对齐）
- [x] 构建验证通过（`idf.py build`）

### 已完成：Phase C 第 2 步（首批）

- [x] `app_rs485_master` 完成低风险对齐：任务创建由绑核改为通用任务创建（与 151_l3 一致）
- [x] `rs485_master_thread_entry` 句柄访问路径统一（`master` 命名与调用路径一致）
- [x] 修复分区特效枚举兼容：补充 `LIGHT_PIXEL_FX_PARTITION -> LIGHT_PIXEL_FX_PARTITON` 别名
- [x] 构建验证通过（`idf.py build`）

### 已完成：Phase C 第 2 步（续，diff 清零审计）

- [x] 完整审计剩余 diff（firmware extern 声明 + if 格式 + 空白行）
- [x] firmware extern：当前工程已通过 `#include "point_light_firmware.h"` 管理，比 151_l3 行内 extern 更规范，**不做改动**
- [x] if 语句格式差异：纯风格，功能等价，**不做改动**
- [x] Phase C 第 2 步全部差异已闭环（substantive diff 清零）

**Phase C 第 2 步总结：已完成**（`app_rs485_master` 低风险对齐全部落地，剩余 diff 均属设计优势或不影响行为的格式差异）

---

## 11. 下一步建议

### 选项 A（推荐）：Phase B 实机回归
优先上板验证，通过日志判读确认 pixel_fx 双路径工作正常后，再决策是否继续深入 Phase C。

**回归要点（`pixel_fx_task` 30s 周期日志）：**
- `new_load_ok > 0`：新引擎路径命中
- `fallback_count == 0`：无回退
- 多轮模式切换后 `mode_switch_count` 正常递增，无残留

### 选项 B：Phase C 第 3 步决策
基于实机数据决定是否进一步对齐 `app_light` 内部控制逻辑（state_manager 主链路不动）。

### 选项 C：其他功能（MQTT TLS 联调、BLE 验证等）

## 12. 2026-05-19 增量审计：151_l3 `9ed22c0`

审计范围:

- 基线提交: `ad08ac0`
- 最新上游: `9ed22c0`
- 审计目标: 只识别 `ad08ac0..9ed22c0` 的新增差异，避免重复追已经完成的 Phase A/B/C 内容

### 12.1 本次上游变化摘要

`9ed22c0` 的提交说明是：

- 缓变定时器改成软件定时器
- 单路 SPI 驱动改成双路驱动
- 优化 485 主机逻辑

结合实际 diff，额外还包含:

- point-light 配置头调整
- sync_time 地理位置获取增加初始等待与重试退避
- BLE 模块 reset 管脚调整
- ambient Wi-Fi 默认密码调整
- 新增 legacy `app_rs485_slave.c`

### 12.2 增量迁移判断

| 上游变化摘要 | 当前工程活跃落点 | 迁移状态 | 最小安全动作 |
|---|---|---|---|
| `dev_lamp/app_light` 把 1ms 灯控回调默认切到 FreeRTOS 软件定时器 | `components/drivers/dev_lamp/dev_lamp.c` | 已对齐 | 当前工程已经默认走 `xTimerCreate()` 软件定时器，并保留硬件 ISR 作为回滚路径，无需重复迁移 |
| `dev_ws28xx` 从单 SPI encoder 变成按段分发的双 SPI encoder，并在头文件里引入 `WS28XX_SPI_LAYOUT` / segment 宏 | `components/drivers/dev_ws28xx/include/dev_ws28xx.h` + `components/drivers/dev_ws28xx/led_spi_strip_encoder.c` | 已同步 | 当前工程已引入上游的分段 encoder 抽象和单/双 SPI 配置宏；2026-05-19 在确认存在第二路灯带和 SPI3 走线后，默认布局已切到 dual，且第一段 MOSI 已按 151_l3 对齐到 GPIO15 |
| `app_rs485_master` 改版本号解析口径、增加更保守的重试节奏，并在 reconnect 后重灌当前状态 | `main/app/app_rs485_master.c` | 已同步 | 当前工程已用 `state_store` 完成首次连接/重连回灌，且额外支持主动上报与 Matter 回写；2026-05-19 已补上 `*_revision` 版本解析、命令 `100ms` 重试间隔与温度查询重试 |
| `project_config.h` 对 point-light 继续固定 `LAMP_L3` | `components/lighting/los_sta_data/include/project_config.h` + `components/drivers/dev_lamp/dev_lamp.c` | 已同步 | 当前工程已在 `CONFIG_PRODUCT_IS_POINT_LIGHT=y` 时同时定义 `POINT_CONFIG` 与 `LAMP_L3`，使 point-light profile 与 legacy PWM 通道布局一致 |
| `sync_time` 增加地理位置查询初始等待、失败退避与更稳健的资源清理 | `components/network/sync_time/include/config.h` + `components/network/sync_time/geo_location.c` + `components/network/sync_time/timezone_sync.c` | 已同步 | 当前工程已补 `GEO_API_INITIAL_DELAY_MS`、指数退避重试和地理位置查询重试日志，同时保持现有 HTTPS/crt bundle 配置 |
| BLE reset pin 从 `6` 改到 `21` | `components/network/at/dev_sidus_ble.c` | 已同步 | 在确认当前板级沿用 151_l3 走线后，Sidus BLE reset 已按上游对齐到 GPIO21 |
| ambient Wi-Fi 默认密码从 `soft.123` 改到 `apiot.123` | `components/network/cmd_wifi/include/ambient_config.h` | 不建议直接迁移 | 属于产品默认配置，不是框架行为差异 |
| 新增 legacy `main/app_rs485_slave.c` | 当前工程无活跃等价入口 | 不建议直接迁移 | 当前仓库主链仍是 `main/main.cpp::app_main -> components/app/local_output`，没有保留 legacy slave 入口 |

### 12.3 当前最值得继续跟进的项

本轮 `9ed22c0` 增量对应的低风险可迁移项已经完成。`dev_ws28xx` 的双 SPI 默认启用条件也已具备，因此这里没有新的必做同步项。

### 12.4 这轮审计后的结论

- `9ed22c0` 不是一次“整仓都要重新迁”的提交。
- 本轮识别出的可安全迁移行为已经全部完成；后续只需继续盯板级冲突与资源复用。
- 其中 `dev_lamp` 的软件定时器切换，当前工程已经先行对齐。
- `app_rs485_master` 主体并不落后，反而是当前工程更强；2026-05-19 这轮已经补齐了本次上游提交涉及的关键 legacy 语义与稳定性调优，不需要回退到 `temp_db` 写法。
- `dev_ws28xx` 的软件架构差异已经补齐；在确认第二路灯带和 SPI3 走线存在后，默认双 SPI 布局已正式启用，第一段 MOSI 也已按 151_l3 对齐到 GPIO15。
- 2026-05-19 已把当前仓库中误落到 GPIO38 的 RS485 DIR 迁回 GPIO3，并同步把 `app_power.c` 的音频 ADC 通道/校准统一到 `ADC_CHANNEL_7(GPIO8)`，避免把 151_l3 中“GPIO3 同时挂 RS485 DIR 与 ADC_CHANNEL_2 校准”的历史遗留继续带入现仓。
- 2026-05-19 已新增 `board_pin_checks.h` 编译期校验，后续若再把 `RS485/WS28xx/Ambient/BLE/Debug/Button/Aux` 等板级 GPIO 配成重复占用，将直接在编译阶段静态断言失败。
- 2026-05-19 已把 `AUDIO_ADC_GPIO8` 也纳入编译期保留脚检查，后续若把音频 ADC 采样脚误配给任一数字功能，同样会在编译阶段直接失败。

## 13. 2026-05-20 增量审计：151_l3 `5f33117`

审计范围:

- 基线提交: `9ed22c0`
- 最新上游: `5f33117`
- 审计目标: 只识别 `9ed22c0..5f33117` 的新增差异，确认当前仓库是否还存在需要继续迁移的行为

### 13.1 本次上游变化摘要

`5f33117` 的提交说明是：

- 同步点光源开关状态到系统状态数据库
- 增加从机功能用做采集基础数据

结合实际 diff，核心变化可以压缩成 5 项：

- `main/app_rs485_master.c` 新增 `RS485_Cmd_Switch` 读查询，并把查询到的点光源开关写回 `sys_status.point_on_off`
- `modules/los_sta_data/include/los_data.h` 为 `struct sys_status` 新增 `point_on_off`
- `main/point_light_firmware.h` 更新了整份点光源内置固件正文，头部版本与 CRC 均变化
- `components/dev_lamp/dev_lamp.c` 在灯任务初始化阶段额外拉高一路辅助 PWM
- `main/app_rs485_slave.c` 继续扩展 legacy slave 侧处理

### 13.2 增量迁移判断

| 上游变化摘要 | 当前工程活跃落点 | 迁移状态 | 最小安全动作 |
|---|---|---|---|
| `app_rs485_master` 把点光源开关状态单独写入 `sys_status.point_on_off` | `main/app/app_rs485_master.c` + `main/light/state_store.c` + `components/lighting/los_sta_data/include/los_data.h` | 已同步 | 2026-05-20 已补 `sys_status.point_on_off` 与 `state_store_get/set_point_power_on()`，并在 RS485 轮询/重连回灌中同步点光源开关状态 |
| `los_data.h` 为 `struct sys_status` 新增 `point_on_off` | `components/lighting/los_sta_data/include/los_data.h` | 已同步 | 状态结构与本地数据库初始化已经同步扩展，避免主站写入落空 |
| `point_light_firmware.h` 更新点光源内置固件正文 | `main/proto/point_light_firmware.c` + `main/app/app_rs485_master.c` | 已同步 | 2026-05-20 已机械同步 151_l3 `5f33117` 的最新固件 blob，当前升级入口无需改动 |
| `dev_lamp.c` 在任务启动时额外设置一路辅助 PWM 为 100% | `components/drivers/dev_lamp/dev_lamp.c` | 不建议直接照搬 | 当前工程已重构为 `aux_output_init_if_needed()` + 双辅助 PWM 输出模型；除非先确认板级电源门控需求，否则不要把 legacy 单点初始化直接贴回现架构 |
| legacy `app_rs485_slave.c` 继续扩展 | 当前仓库无活跃等价入口 | 不建议直接迁移 | 当前活跃入口仍是 `main/main.cpp::app_main`，没有保留 legacy slave 独立线程主链 |

### 13.3 已对齐或已增强的项

虽然 `5f33117` 改了 `main/app_rs485_master.c`，但其中一批稳态能力当前仓库已经提前具备或已增强，不应误判为缺口：

- 周期状态定时器已经存在，且当前工程已经有 `status_timer`
- 固件传输头结构已经包含 `firmware_crc`
- 首次连接和重连后的状态回灌已经保留，并由 `state_store` 承接
- `RS485_Cmd_Switch` 的查询能力当前工程已经存在，且比 legacy 还额外覆盖了 `Factory_RGBWW` 查询和主动上报解析

因此本次真正新增的未对齐项，不是整份 `app_rs485_master.c`，而是“点光源开关独立状态字段”和“最新内置固件正文”。

### 13.4 这轮审计后的结论

- `5f33117` 在当前仓库并不是大面积回归风险，真正需要迁移的缺口已经在 2026-05-20 收口完成。
- `main/proto/point_light_firmware.c` 已切到上游最新点光源固件正文，`app_rs485_master` 的升级入口保持不变。
- `sys_status.point_on_off` 已作为当前仓库中的点光源从机开关状态单独保留，并通过 `state_store` 与 RS485 主站轮询/重连路径同步。
- `dev_lamp` 的辅助 PWM 初始化和 legacy slave 扩展都不适合按文件差异直接回贴，需继续遵守当前仓库的 framework/local_output 分层。

## 14. 2026-05-21 增量审计：151_l3 `691ab58` 与 `077b47f`

审计范围:

- 基线提交: `5f33117`
- 最新上游: `077b47f`
- 审计目标: 只识别 `5f33117..077b47f` 的新增差异，并判断当前仓库哪些需要继续迁移

### 14.1 本次上游变化摘要

`691ab58` 的提交说明是：

- 优化 485 驱动
- 优化 485 升级逻辑
- 优化灯光控制逻辑
- 增加温度等获取

`077b47f` 的提交说明是：

- 优化按键有效电平
- 优化 485 发送 HSI 数据的计算方式

结合实际 diff，这两笔提交可以归纳为 6 项：

- `main/app_use_btn.c` 把 back button 的 `pressed_logic_level` 从 `0` 改到 `1`
- `main/app_rs485_master.c` / `utilities/protocol/trans_rs485_and_light_ctrl.c` 修正 HSI 下发单位，把 `hue/sat` 从 `0-360 / 0-100` 转成协议要求的 `0-36000 / 0-10000`
- `main/app_rs485_master.c` 保持温度查询与命令重试路径的小幅整理
- `modules/rs485/port/rs485_port_esp.c` 改为依赖 ESP-IDF 的 `UART_MODE_RS485_HALF_DUPLEX` 和更稳健的收包拼帧
- `main/app_power.c` 恢复 legacy 的多 ADC 通道采样和 COB 温度回写
- 新增 `utilities/protocol/trans_rs485_and_light_ctrl.*`，把 `light_ctrl <-> RS485` 的互转逻辑从 `app_rs485_master.c` 中拆出来

### 14.2 增量迁移判断

| 上游变化摘要 | 当前工程活跃落点 | 迁移状态 | 最小安全动作 |
|---|---|---|---|
| `app_use_btn.c` 把 `pressed_logic_level` 调整为 `1` | `main/app/app_use_btn.c` | 已对齐 | 当前仓库工作树已与上游一致，无需重复迁移 |
| HSI 下发单位修正到 `0-36000 / 0-10000` | `main/app/app_rs485_master.c` | 已同步 | 2026-05-21 已按当前仓库活跃主链补齐 `rs485_hsi_t.hue/sat` 的 `*100` 缩放，不引入 legacy translator 文件 |
| `app_rs485_master.c` 的温度查询/重试细节整理 | `main/app/app_rs485_master.c` | 已对齐 | 当前仓库已保留 `100ms` 重试节奏和温度查询日志，无需重复迁移 |
| `rs485_port_esp.c` 改为 `UART_MODE_RS485_HALF_DUPLEX` + 拼帧式接收 | `components/drivers/rs485/port/rs485_port_esp.c` | 部分迁移 | 当前仓库端口层已对齐 DIR=GPIO3 和基本时序，但仍保留自管 DIR 模式；只有在后续出现半双工收包边界问题时，再做最小端口级迁移 |
| `app_power.c` 恢复 legacy 多 ADC 通道 + COB 温度 ADC | `main/app/app_power.c` | 不建议直接迁移 | 当前仓库已切到 `temperature_sensor + state_store` 的温控链，不应回退到 legacy 多路 ADC 采样结构 |
| 新增 `trans_rs485_and_light_ctrl.*` | `main/app/app_rs485_master.c` + `components/lighting/fx_structure_tools/` | 不建议直接迁移 | 当前仓库 RS485 与 Matter/FX 桥接已经拆到现有层次，只需吸收行为差异，不应把 legacy translator 整文件贴回 |

### 14.3 当前结论

- `077b47f` 不是整仓迁移，而是两项小修：按键有效电平和 HSI 协议单位。
- 按键有效电平当前仓库已经对齐；真正的行为缺口是 HSI 下发单位，这一项已在 2026-05-21 收口完成。
- `691ab58` 中值得继续关注的是 RS485 端口层的半双工接收改造，但这不是当前日志下的确定性缺口；现阶段先保持现有端口实现，避免把 legacy 串口层整段覆盖进当前框架。
- `app_power.c` 和新增 translator 文件都属于 legacy 架构实现细节，当前仓库已有更合适的承接层，不建议按文件级直接迁移。

## 15. 2026-05-22 重评估：以“完整保留 151 功能”为第一原则

本节覆盖此前文档中的一个默认前提：

- 旧前提：只迁当前仓库真正缺少且值得保留的行为；对于有更高层替代的 legacy 文件，可以标为“不建议迁移”。
- 新前提：151_l3 的已有功能应完整保留；当前仓库允许重构、分层和增强，但不能以“当前有新架构”为理由永久放弃 legacy 功能面。

在这个新前提下，之前一些“不建议迁移”的结论需要重新分类：

- 若某个 151 功能当前仓库没有等价入口、等价行为或兼容模式，则应归类为“功能缺口”，而不是继续标为“不建议迁移”。
- 若某个 151 功能已由当前仓库的其他层完整承接，则仍可视为“已保留”，不要求同名文件回归。
- 若某个 151 功能只保留了部分语义，则应归类为“部分保留”，并列入兼容待办。

### 15.1 新的判定标准

按“完整保留 151 功能”重新判定时，迁移状态改按以下口径理解：

- 已完整保留：151 的功能入口或等价行为已存在，且当前工程只是换了架构落点。
- 部分保留：主能力还在，但缺少某些 legacy 入口、模式或兼容 API。
- 功能缺口：151 有明确功能，当前仓库没有等价实现，也没有兼容模式。
- 架构增强：当前仓库新增了更高层能力，但这不能自动抵消 legacy 功能缺口。

### 15.2 在新前提下需要改判的项

| 151 功能 | 151 活跃入口 | 当前工程活跃落点 | 旧判定 | 新判定 | 说明 |
|---|---|---|---|---|---|
| RS485 从机线程 | `main/app_rs485_slave.c` | 当前无编译入口 | 不建议迁移 | 功能缺口 | 当前仓库只有 `app_rs485_master` 的主站/主动上报处理，没有“收命令 -> 应用灯态 -> 回 ACK”的独立从机服务 |
| 控制台初始化层 | `main/console_settings.c/h` | 当前 `main/main.cpp` 未显式接入等价入口 | 未迁移 | 功能缺口 | `cmd_system/cmd_nvs` 组件仍在，但缺少 151 的 console 外设初始化、linenoise/history、prompt 建立与统一入口 |
| 通用 RS485 <-> light_ctrl 双向转换 API | `utilities/protocol/trans_rs485_and_light_ctrl.*` | 当前无同级 API | 不建议直接迁移 | 功能缺口 | 当前仓库只在 `app_rs485_master.c` 内局部保留发送侧转换；缺少供 slave/协议桥复用的通用双向 helper |
| RS485 端口半双工模式与拼帧接收 | `modules/rs485/port/rs485_port_esp.c` | `components/drivers/rs485/port/rs485_port_esp.c` | 部分迁移 | 部分保留 | 已对齐 GPIO3 和基本时序，但未完全吸收 `UART_MODE_RS485_HALF_DUPLEX` 和更稳健的 frame assembly |
| legacy 多 ADC 通道与 COB 温度采集 | `main/app_power.c` | `main/app/app_power.c` | 不建议直接迁移 | 部分保留 | 当前仓库保留了 `led_temp/over_temp` 状态面，但采集链已改成 `temperature_sensor` 主导，legacy 多通道 ADC 语义未完整保留 |
| 点光源辅助 PWM 启动语义 | `components/dev_lamp/dev_lamp.c` | `components/drivers/dev_lamp/dev_lamp.c` | 不建议直接照搬 | 部分保留 | 当前仓库已通过双辅助 PWM 模型和 GPIO1 常高修复保留关键硬件语义，但是否完全等价于 151 的启动阶段上电门控，仍需板级验证 |

### 15.3 在新前提下仍可视为“已完整保留”的项

以下能力虽然没有按 151 原文件布局保留，但从功能面看已经被当前仓库完整承接，不应误记为缺口：

- `main/app_rs485_master.c` 的主站、固件升级、状态轮询、重连回灌主链
- `main/point_light_firmware.h` 对应的点光源内置固件正文
- `components/dev_lamp`、`dev_ws28xx`、`light_effect_pixel`、`SidusProFX`、`fx` 等灯光与驱动主链
- `sys_status.point_on_off`、`sys_status.led_temp` 等关键状态面
- `cmd_system`、`cmd_nvs` 这些 console 子命令组件本身

换句话说，新原则不是要求“把 151 的目录结构原样搬回来”，而是要求“151 的功能面不能丢”。

### 15.4 新前提下的最小安全迁移路线

如果目标改为“完整保留 151 功能，并在此基础上继续开发当前工程”，则优先级应调整为：

1. 先补兼容入口，而不是回退当前架构。
2. 所有新增兼容能力，都应落到当前主链的真实入口上：`main/main.cpp::app_main` 和 `components/app/local_output`。
3. 优先补那些当前完全缺失的 legacy 功能，再补“只有部分保留”的项。

建议的落点如下：

| 待补能力 | 当前仓库建议落点 | 最小安全做法 |
|---|---|---|
| `app_rs485_slave` | `components/app/local_output/CMakeLists.txt` + `main/app/app_rs485_slave.c` | 以可选编译单元方式恢复 slave 线程，不改变当前 `app_main -> local_output` 主链 |
| `console_settings` | `main/` 下新增兼容层或 `components/console/` 下新增 bootstrap | 恢复 console 外设初始化与 prompt/history 建立，再复用现有 `cmd_system/cmd_nvs` 组件 |
| `trans_rs485_and_light_ctrl` | 优先放到 `components/drivers/rs485/` 或 `components/network/bluetooth_protocol_compat/` 旁的协议兼容层 | 提供 `light_ctrl_to_rs485()` / `rs485_to_light_ctrl()` 通用 API，供 master/slave/桥接共享 |
| `app_power` legacy ADC 语义 | `main/app/app_power.c` 内通过 Kconfig 或 profile 开关保留兼容采集路径 | 保持现有 `temperature_sensor` 主链，同时允许 point-light profile 启用 legacy ADC 兼容模式 |
| `rs485_port_esp` 半双工增强 | `components/drivers/rs485/port/rs485_port_esp.c` | 以最小差异吸收 half-duplex 和拼帧逻辑，不回退当前板级引脚与防冲突校验 |

### 15.5 重评估后的总判断

在“完整保留 151 功能”的目标下，当前仓库不能再被描述为“151 功能已基本迁完，只剩局部优化”。

更准确的结论是：

- 灯光主链、RS485 主站主链、驱动主链大部分已保留，且很多地方已经增强。
- 但仍有一批 151 的 legacy 功能入口没有保留下来，尤其是 `app_rs485_slave`、`console_settings`、通用 `trans_rs485_and_light_ctrl` API。
- 这些项在旧口径下可以被视为“当前架构不需要”；但在新口径下，它们都应被纳入正式迁移待办，而不是继续标为“不建议迁移”。

因此，从 2026-05-22 起，若继续按“完整保留 151 功能”推进，本仓库的迁移状态应改写为：

- 主功能链：大体保留并增强
- 兼容功能链：仍有明确缺口
- 后续迁移重点：补齐兼容入口，而不是回退当前框架

## 16. 151 全功能保留待办表（第一版，暂不含 console）

本节只列出“完整保留 151 功能”目标下，除 `console_settings` 之外的正式待办。

写法约束:

- 每个条目都按“上游事实 / 当前状态 / 目标状态 / 可执行任务”拆开。
- 任务描述尽量落到当前仓库真实入口，不用 legacy 文件路径替代当前活跃落点。
- 优先补兼容入口与兼容 API，不回退 `local_output / light_control_bus / DeviceCallbacks / state_store` 这些现有骨架。

### 16.1 总表

| 待办ID | 缺口主题 | 上游事实 | 当前状态 | 目标状态 | 建议优先级 | 当前仓库优先落点 |
|---|---|---|---|---|---|---|
| BF-01 | RS485 从机线程兼容保留 | 151 有独立 `app_rs485_slave.c`，可收 CCT / Factory_RGBWW 命令并回 ACK | 已增加可选兼容 slave 入口，默认关闭，开启后替代默认 master 启动路径 | 当前仓库可选启用兼容 slave 线程，且不破坏主链 | P0 | `main/app/app_rs485_slave.c` + `components/app/local_output/CMakeLists.txt` + `main/app/local_manager.c` |
| BF-02 | 通用 `trans_rs485_and_light_ctrl` API | 151 有 `light_ctrl_to_rs485()` / `rs485_to_light_ctrl()` 双向 helper | 已恢复仓级 helper，并由当前 master 发送路径复用 | 恢复仓级通用 API，供 master / slave / 桥接复用 | P0 | `components/drivers/rs485/` 邻近兼容层，或 `main/app/` 可复用 helper |
| BF-03 | `app_light` legacy 语义补齐 | 151 的 `app_light.c` 内含 DB 同步、上电恢复、预处理、应用前缓存逻辑 | 当前接口在，但语义拆到 facade/state_store/bus，多数已保留，仍缺逐项对账 | 得到一份逐行为闭环的 parity matrix，并收口剩余差异 | P1 | `main/app/app_light.c` + `main/light/light_control_facade.c` + `main/light/state_store.c` |
| BF-04 | `app_rs485_master` legacy 行为闭环 | 151 主站除主链外还包含边缘查询、异常恢复、转换复用等语义 | 当前主链增强较多，但仍缺基于“151 全功能面”的闭环对账 | 形成命令矩阵、异常恢复矩阵，并补齐剩余 legacy 行为 | P1 | `main/app/app_rs485_master.c` |
| BF-05 | RS485 端口 half-duplex / 拼帧能力 | 151 端口层显式用了 `UART_MODE_RS485_HALF_DUPLEX` 和更稳健的分段收包 | 当前端口可工作，但未完整吸收这套行为 | 在不改板级 GPIO 与冲突校验的前提下补齐端口语义 | P1 | `components/drivers/rs485/port/rs485_port_esp.c` |
| BF-06 | `app_power` legacy ADC 兼容模式 | 151 用多 ADC 通道采集音频/硬件版本/COB 温度/输入电压等 | 当前以 `temperature_sensor` 主导，legacy 多通道语义未完整保留 | 保持现主链默认不变，同时提供 point-light profile 兼容采集模式 | P2 | `main/app/app_power.c` |
| BF-07 | `dev_lamp` 启动期辅助 PWM 语义对齐 | 151 在启动/上电门控阶段有额外辅助 PWM 置位语义 | 当前已保留 GPIO1 常高等关键行为，但启动序列是否完全等价尚未验证 | 在板级验证基础上补齐 profile-specific 启动门控语义 | P2 | `components/drivers/dev_lamp/dev_lamp.c` |
| BF-08 | 启动编排兼容清单 | 151 的 `main/main.c` 负责编排一系列 local feature init | 当前编排拆到 `main/main.cpp + local_manager.c`，功能多数仍在 | 补出“151 启动职责 -> 当前入口”的任务清单，确保没有遗漏服务 | P2 | `main/main.cpp` + `main/app/local_manager.c` |

### 16.2 BF-01: RS485 从机线程兼容保留

上游事实:

- 151 的 `main/app_rs485_slave.c` 是一个独立线程。
- 它负责接收 RS485 写命令、把 `CCT / Factory_RGBWW` 转成 `light_ctrl`、调用 `lamp_set_pixel()`，并回 ACK。

当前状态:

- 当前仓库已新增 `main/app/app_rs485_slave.c` 与 `app_rs485_slave_init()`。
- 通过 `CONFIG_LOCAL_OUTPUT_ENABLE_RS485_SLAVE_COMPAT` 可选启用 151 风格 slave 线程。
- `main/app/local_manager.c` 在该开关打开时启动 slave，并跳过默认 `app_rs485_master_init()`，避免同一 UART 同时起主站和从机。
- slave 当前复用了 BF-02 的 `rs485_to_light_ctrl()`，已覆盖 `CCT / HSI / Factory_RGBWW / ACK` 主路径。

目标状态:

- 当前仓库能以“可选兼容模式”恢复 151 的从机能力。
- 恢复后不改变 `main/main.cpp::app_main -> local_output` 主链，不与现有 RS485 主站默认路径互相覆盖。

进展更新（2026-05-22）:

- BF-01-02 至 BF-01-06 已完成首版落地。
- 已完成整仓 `idf.py build` 编译验证。
- BF-01-07 仍待真实串口联调确认 `CCT / Factory_RGBWW -> ACK` 闭环日志。

可执行任务:

| 子任务ID | 动作 | 验收标准 |
|---|---|---|
| BF-01-01 | 从 151 提取 `app_rs485_slave.c` 的命令覆盖面，只保留当前已确认需要兼容的 `CCT / Factory_RGBWW / ACK` 主路径 | 形成一份最小命令清单，避免先整文件照搬 |
| BF-01-02 | 在 `main/Kconfig.projbuild` 增加兼容开关，例如 `LOCAL_OUTPUT_ENABLE_RS485_SLAVE_COMPAT` | 该能力可按 profile 启闭，默认不影响当前主链 |
| BF-01-03 | 在当前仓库新增 `main/app/app_rs485_slave.c` 兼容实现，并适配当前 include / 驱动路径 | 文件能进入当前工程构建，不依赖 151 的原始目录结构 |
| BF-01-04 | 在 `components/app/local_output/CMakeLists.txt` 里按 Kconfig 条件加入 slave 源文件 | 打开开关后 slave 代码进入编译；关闭时无副作用 |
| BF-01-05 | 在 `main/app/local_manager.c` 中按配置选择性初始化 slave 服务 | 兼容模式打开时初始化一次；不开启时行为不变 |
| BF-01-06 | slave 内部优先复用 BF-02 的通用转换 API，而不是复制 master 的局部逻辑 | slave 与 master 不再各维护一套转换逻辑 |
| BF-01-07 | 增加最小联调验证：写 `CCT`、写 `Factory_RGBWW`、收到 ACK | 至少完成三项串口联调日志闭环 |

### 16.3 BF-02: 通用 `trans_rs485_and_light_ctrl` API

上游事实:

- 151 有独立 `trans_rs485_and_light_ctrl.h/.c`。
- 它提供发送侧 `light_ctrl_to_rs485()` 与接收侧 `rs485_to_light_ctrl()`，可供 master/slave 共享。

当前状态:

- 当前仓库已新增 `main/app/trans_rs485_and_light_ctrl.h/.c`。
- `app_rs485_master.c` 的发送侧已改为调用 `light_ctrl_to_rs485()`。
- BF-01 新增的 slave 兼容线程已复用 `rs485_to_light_ctrl()`。

目标状态:

- 当前仓库恢复通用双向转换 API。
- master、未来的 slave、以及后续协议桥接都复用同一套转换语义。

进展更新（2026-05-22）:

- BF-02-01 至 BF-02-06 已完成首版实现。
- 当前 helper 已覆盖 `HSI / CCT / PWM / XY / Sys_FX` 发送侧转换，以及 `CCT / HSI / Factory_RGBWW` 接收侧转换。
- BF-02-07 仍待补最小测试用例，目前先以整仓编译通过作为阶段性验证。

可执行任务:

| 子任务ID | 动作 | 验收标准 |
|---|---|---|
| BF-02-01 | 选定兼容层落点，优先靠近 `components/drivers/rs485/` 或 `main/app/` 现有 RS485 代码 | 确定一个稳定公共 include 路径 |
| BF-02-02 | 迁入 `trans_rs485_and_light_ctrl.h` 的最小 API 面，只暴露 `light_ctrl_to_rs485()` / `rs485_to_light_ctrl()` | 头文件职责清晰，不引入 151 私有路径依赖 |
| BF-02-03 | 迁入发送侧转换逻辑，并保留当前仓库已修正的 HSI 单位缩放 | `HSI/CCT/PWM/Sys_FX` 转换结果与当前协议头一致 |
| BF-02-04 | 迁入接收侧转换逻辑，优先覆盖 `CCT/HSI/Factory_RGBWW` | slave 与后续桥接至少能复用这三类命令转换 |
| BF-02-05 | 将 `app_rs485_master.c` 的内联转换逻辑重构为调用新 helper | master 功能不变，代码路径更统一 |
| BF-02-06 | 为 BF-01 的 slave 实现接入同一 helper | slave 不再复制转换逻辑 |
| BF-02-07 | 补一组最小单元或组件测试，至少验证 `HSI/CCT/PWM` 三类互转 | 转换输出能稳定复现 |

### 16.4 BF-03: `app_light` legacy 语义补齐

上游事实:

- 151 的 `app_light.c` 不只是线程入口，还承接 DB 同步、上电恢复、应用前预处理、状态记录等语义。

当前状态:

- 当前仓库保留了 `app_light_send_msg()`、`app_light_prepare_power_on_ctrl()` 等接口。
- 但 legacy 语义已拆散到 `light_control_facade / state_store / light_control_bus`，需要逐项对账。

目标状态:

- 得到一份“151 app_light 行为矩阵 -> 当前落点 -> 是否已闭环”的清单。
- 真缺口收敛为小补丁，而不是长期停留在“部分迁移”。

可执行任务:

| 子任务ID | 动作 | 验收标准 |
|---|---|---|
| BF-03-01 | 从 151 `app_light.c` 抽取行为矩阵：上电恢复、分区缓存、预处理、应用后记录、信号量/队列模型 | 形成一份子行为清单 |
| BF-03-02 | 把每个子行为映射到当前 `app_light.c / facade / bus / state_store` 的真实落点 | 不再用“整文件部分迁移”描述模糊结论 |
| BF-03-03 | 标出缺失或仅部分保留的子行为 | 形成明确 gap list |
| BF-03-04 | 对缺失子行为给出最小落点补丁方案，优先落在 facade/state_store 而非回贴 legacy 单文件 | 补丁面可执行 |
| BF-03-05 | 做最小回归项：上电恢复、命令应用前后状态一致性、分区模式切换 | 三项行为与 151 一致或有文档化差异说明 |

### 16.5 BF-04: `app_rs485_master` legacy 行为闭环

上游事实:

- 151 的 `app_rs485_master.c` 除主链外，还隐含命令覆盖、异常恢复、查询节奏、升级边界处理等行为。

当前状态:

- 当前仓库主站能力更强，但“增强”不等于“151 功能面已完全闭环”。

目标状态:

- 明确哪些是已增强替代，哪些仍是 legacy 缺口。
- 把“部分迁移”收敛成可执行子任务，而不是长期挂起。

可执行任务:

| 子任务ID | 动作 | 验收标准 |
|---|---|---|
| BF-04-01 | 形成 151 `app_rs485_master` 的命令覆盖矩阵（发送/查询/解析/升级） | 每个命令都有状态标签 |
| BF-04-02 | 形成异常恢复矩阵：首次连通、重连、超时、ACK 错误、升级失败、主动上报恢复 | 每类异常都能映射到当前仓库处理路径 |
| BF-04-03 | 把已增强替代与真正缺口分开记录 | 减少“看起来没迁”的误判 |
| BF-04-04 | 对真正缺口按最小行为补丁落到当前 `app_rs485_master.c` | 不引入 legacy 结构回退 |
| BF-04-05 | 完成一轮串口联调用例：版本查询、温度查询、重连回灌、升级起始/失败路径 | 至少四项日志闭环 |

### 16.6 BF-05: RS485 端口 half-duplex / 拼帧能力

上游事实:

- 151 的 `rs485_port_esp.c` 显式使用 `UART_MODE_RS485_HALF_DUPLEX`。
- 它还比当前仓库更强调按 header 的 `msg_size` 做分段接收与拼帧。

当前状态:

- 当前端口层已能工作，并已对齐当前板级 GPIO 与冲突校验。
- 但 half-duplex 与拼帧语义仍未完全承接。

目标状态:

- 在不影响当前板级配置和现有主链的前提下，补齐端口层兼容行为。

可执行任务:

| 子任务ID | 动作 | 验收标准 |
|---|---|---|
| BF-05-01 | 对照 151 的 `port_send/port_recv`，列出 half-duplex 和 frame assembly 的明确行为差异 | 差异点不再停留在笼统描述 |
| BF-05-02 | 设计兼容引入方式：直接吸收或通过 Kconfig/profile 切换 | 不影响当前稳定路径 |
| BF-05-03 | 补齐 `port_recv` 的按 header 长度拼帧逻辑 | 分段到达报文能完整收齐 |
| BF-05-04 | 评估是否安全引入 `UART_MODE_RS485_HALF_DUPLEX`，并验证不破坏当前 DIR 控制策略 | half-duplex 方案有明确启用条件 |
| BF-05-05 | 做串口压力验证：拆包、粘包、缓冲区溢出恢复 | 端口层日志可证明行为稳定 |

### 16.7 BF-06: `app_power` legacy ADC 兼容模式

上游事实:

- 151 的 `app_power.c` 承担多通道 ADC 采样，包含音频、硬件版本、COB 温度、VIN 等语义。

当前状态:

- 当前仓库保留了 `led_temp/over_temp` 等状态面。
- 但主要依赖 `temperature_sensor`，legacy ADC 采样面并未完整保留。

目标状态:

- 当前仓库默认仍使用现有稳定主链。
- 同时对 point-light 或兼容 profile 提供 legacy ADC 语义保留路径。

可执行任务:

| 子任务ID | 动作 | 验收标准 |
|---|---|---|
| BF-06-01 | 从 151 抽取 `app_power.c` 的完整 ADC 语义清单：哪些通道、写哪些状态字段、用于哪些功能 | 得到明确需求面 |
| BF-06-02 | 将语义清单映射到当前 `sys_status`，确认哪些字段已保留、哪些仅靠 `temperature_sensor` 间接覆盖 | 状态面对账完成 |
| BF-06-03 | 设计兼容 profile 开关，不改变默认稳定配置 | 默认构建行为不退化 |
| BF-06-04 | 在兼容 profile 下恢复必要 ADC 通道采样和状态写回 | `led_temp` 等字段来源可切换 |
| BF-06-05 | 做最小验证：兼容模式开关、温度写回、音频采样不回归 | 兼容模式可控且可验证 |

### 16.8 BF-07: `dev_lamp` 启动期辅助 PWM 语义对齐

上游事实:

- 151 在 `dev_lamp` 启动阶段有额外辅助 PWM 置位和门控语义。

当前状态:

- 当前仓库已经为实际板级问题补过 GPIO1 常高等修复。
- 但“启动期是否完全等价于 151”还没有形成结论。

目标状态:

- 给出明确板级结论：当前双辅助 PWM 模型是否已完整覆盖 151 语义；若没有，则通过 profile-specific hook 补齐。

可执行任务:

| 子任务ID | 动作 | 验收标准 |
|---|---|---|
| BF-07-01 | 提取 151 `dev_lamp` 的启动期辅助 PWM 语义 | 明确 legacy 需要保持的硬件行为 |
| BF-07-02 | 对照当前 `aux_output_init_if_needed()` 和 GPIO1/GPIO14 路径 | 差异点被具体列出 |
| BF-07-03 | 在 point-light profile 下引入最小兼容 hook，而不是回退整个驱动 | 驱动架构保持不变 |
| BF-07-04 | 上板验证上电、关灯、重启三个场景 | 三个场景行为可重复验证 |

### 16.9 BF-08: 启动编排兼容清单

上游事实:

- 151 的 `main/main.c` 作为入口，直接串起一系列 local feature init。

当前状态:

- 当前仓库把启动拆到 `main/main.cpp` 与 `main/app/local_manager.c`。
- 多数能力已接入，但尚未形成“151 启动职责全量映射表”。

目标状态:

- 每个 151 启动职责都能在当前入口找到明确落点，或被列为缺口。

可执行任务:

| 子任务ID | 动作 | 验收标准 |
|---|---|---|
| BF-08-01 | 抽取 151 `main/main.c` 的初始化顺序与功能清单 | 得到启动职责列表 |
| BF-08-02 | 映射到当前 `main/main.cpp` 与 `local_manager.c` | 每一项都有当前落点 |
| BF-08-03 | 标出缺失的初始化职责，并按 BF-01/BF-06/BF-07 等待办关联 | 缺失项进入统一 backlog |
| BF-08-04 | 形成“启动编排兼容检查清单”供后续每次移植回归使用 | 启动链验证有固定模板 |

### 16.10 建议执行顺序

推荐先做不会与现有主链强耦合、且能为后续任务复用的项：

1. BF-02 `trans_rs485_and_light_ctrl` 通用 API
2. BF-01 `app_rs485_slave` 兼容入口
3. BF-04 `app_rs485_master` 行为闭环
4. BF-05 RS485 端口 half-duplex / 拼帧增强
5. BF-03 `app_light` 语义补齐
6. BF-07 `dev_lamp` 启动期辅助 PWM 对齐
7. BF-06 `app_power` legacy ADC 兼容模式
8. BF-08 启动编排兼容清单

原因:

- BF-02 是 BF-01/BF-04 的公共前置。
- BF-01 是“完整保留 151 功能”下最明确的功能缺口之一。
- BF-04/BF-05 直接影响 RS485 主链稳定性，应早于外围兼容项。
- BF-06/BF-07 需要更多板级验证，适合放在 RS485 兼容主链稳定之后。