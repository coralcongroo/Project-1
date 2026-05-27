# 151L3 引脚定义结论表

## 文档目的

本文档整理自 /home/ats/git-code/151_l3 当前主工程代码，用于给 Aputure IP Project 做移植、硬件对接和冲突排查参考。

结论范围如下：

- 仅统计 151_l3 主工程实际代码路径中的引脚定义和固定引脚使用。
- 排除 examples、backup、build、managed_components 等非主业务路径。
- 目标芯片按 ESP32-S3 判断。

目标芯片依据：

- /home/ats/git-code/151_l3/sdkconfig 中开启了 CONFIG_IDF_TARGET_ESP32S3。
- /home/ats/git-code/151_l3/README.md 明确说明运行目标为 ESP32-S3。

## 1. GPIO 引脚分配表

| GPIO | 功能定义 | 模块 | 方向 | 上下拉 | 默认电平 | 复用情况 | 风险说明 |
|---|---|---|---|---|---|---|---|
| GPIO1 | PWM_GPIO_1 | 灯光 PWM | 输出 | 未明确 | 未明确 | 与注释中的 ADC_CHANNEL_0 映射重叠 | 当前无运行冲突，但如果恢复多路 ADC 方案可能冲突 |
| GPIO3 | RS485_DIR_PIN | RS485 | 输出 | 未明确 | 未明确 | 与 ADC_CHANNEL_2 映射重叠 | 当前代码只创建了 GPIO3 对应的 ADC 校准句柄，未真正参与换算；若后续恢复 ADC 校准换算，会和 RS485 DIR 形成真实冲突 |
| GPIO4 | DEBUG_TXD_PIN | 调试串口 | 输出 | 未明确 | 未明确 | 与注释中的 ADC_CHANNEL_3 映射重叠 | 当前 ADC 候选仅注释保留，不生效 |
| GPIO5 | DEBUG_RXD_PIN | 调试串口 | 输入 | 未明确 | 未明确 | 与注释中的 ADC_CHANNEL_4 映射重叠 | 当前 ADC 候选仅注释保留，不生效 |
| GPIO7 | RMT_LED_STRIP_GPIO_NUM | WS28xx 灯带 | 输出 | 未明确 | 未明确 | 与非当前目标分支中的 ADC_CHANNEL_6 映射重叠 | 当前目标是 ESP32-S3，实际采样不走 GPIO7，但历史代码容易误导 |
| GPIO8 | ADC_CHANNEL_7 对应脚 | 音频 ADC 采样 | 模拟输入 | 不适用 | 不适用 | 当前无明确数字功能复用 | 当前主采样脚，建议保留纯模拟用途 |
| GPIO9 | RS485_TXD_PIN | RS485 | 输出 | 未明确 | 未明确 | 无明确复用 | 风险低 |
| GPIO10 | RS485_RXD_PIN | RS485 | 输入 | 未明确 | 未明确 | 无明确复用 | 风险低 |
| GPIO12 | 启动阶段控制脚 | 主流程初始化 | 输出 | 代码里使能了上拉 | 启动后拉高 | 休眠流程也使用 | 既参与启动控制，又在休眠时被 isolate，需确认外部电路允许 |
| GPIO13 | 启动阶段控制脚 | 主流程初始化 | 输出 | 代码里继承前一次配置，未单独重设 | 启动后拉高 | 当前未见其他模块复用 | 建议后续显式配置 pull，减少歧义 |
| GPIO14 | PWM_GPIO_14 | 灯光 PWM | 输出 | 未明确 | 未明确 | 无明确复用 | 风险低 |
| GPIO15 | WS2812_PIN | WS2812 SPI 灯带输出 1 | 输出 | 未明确 | 未明确 | 无明确复用 | 风险低 |
| GPIO16 | WS28122_PIN | WS2812 SPI 灯带输出 2 | 输出 | 未明确 | 未明确 | 无明确复用 | 风险低 |
| GPIO17 | SIDUS_BLE_TXD_PIN | Sidus BLE 串口 | 输出 | 未明确 | 未明确 | 无明确复用 | 风险低 |
| GPIO18 | SIDUS_BLE_RXD_PIN | Sidus BLE 串口 | 输入 | 未明确 | 未明确 | 无明确复用 | 风险低 |
| GPIO21 | DEV_SIDUS_BLE_RESET_PIN | Sidus BLE Reset | 输出 | 未明确 | 未明确 | 无明确复用 | 若外部复位脚敏感，建议确认上电默认状态 |
| GPIO37 | KEY1_PIN_NUM | 本地按键 | 输入 | 上拉使能 | 默认高电平推定 | 无明确复用 | 代码写法是位掩码形式，读取时直接传入 gpio_get_level，后续建议核对实现严谨性 |
| GPIO38 | CONFIG_AMBIENT_LED_STRIP_GPIO | Ambient 灯带输出 | 输出 | 未明确 | 未明确 | 无明确复用 | 风险低 |
| GPIO48 | CONFIG_AMBIENT_RGB_CTRL_GPIO | Ambient RGB 总使能 | 输出 | 未明确 | 未明确 | 无明确复用 | 建议确认外设使能脚高低有效关系 |

## 2. ADC 通道与 GPIO 对应表

当前工程目标芯片为 ESP32-S3，因此 app_power.c 中出现的 ADC 通道按 ESP32-S3 做映射。

| ADC 通道 | GPIO | 当前用途 | 状态 |
|---|---|---|---|
| ADC_CHANNEL_0 | GPIO1 | 历史候选 | 注释保留 |
| ADC_CHANNEL_1 | GPIO2 | 历史候选 | 注释保留 |
| ADC_CHANNEL_2 | GPIO3 | 校准句柄创建 | 当前未真正参与采样换算 |
| ADC_CHANNEL_3 | GPIO4 | 历史候选 | 注释保留 |
| ADC_CHANNEL_4 | GPIO5 | 历史候选 | 注释保留 |
| ADC_CHANNEL_7 | GPIO8 | 当前实际采样 | 生效 |

## 3. 当前关键结论

### 3.1 当前实际生效的 ADC 输入脚是 GPIO8

151_l3 当前 app_power 的连续采样配置为 ADC_CHANNEL_7，在 ESP32-S3 上对应 GPIO8。

### 3.2 ADC 校准配置与实际采样通道不一致

当前代码里创建校准句柄时使用的是 ADC_CHANNEL_2，在 ESP32-S3 上对应 GPIO3；但实际采样走的是 ADC_CHANNEL_7，也就是 GPIO8。

不过，这个不一致在当前版本不会造成实际测量错误，原因是校准句柄虽然被创建，但后续采样链路并没有真正调用 adc_cali_raw_to_voltage 做换算，相关代码目前都被注释掉了。

因此该问题的定性是：

- 当前状态：不会直接导致运行时 ADC 数据错误。
- 工程状态：属于明显的遗留配置不一致。
- 后续风险：较高，一旦恢复校准换算，GPIO3 和 GPIO8 不一致会变成真实问题。

### 3.3 当前最需要关注的复用风险是 GPIO3

GPIO3 同时承载以下两种角色：

- RS485 方向控制脚。
- ADC_CHANNEL_2 的映射 GPIO。

虽然当前 ADC 校准值没有真正参与计算，但该复用点是后续最容易演化成故障的地方，应优先清理。

## 4. 建议动作

建议后续在 Aputure IP Project 移植或吸收 151_l3 能力时，优先执行以下动作：

1. 清理 app_power.c 中 ADC 通道与校准通道不一致的问题。
2. 对 GPIO3 做强约束，避免同时承担 RS485 控制和模拟采样职责。
3. 对 GPIO1、GPIO4、GPIO5、GPIO7 的历史 ADC 注释做注解或删除，减少后续维护误判。
4. 对 GPIO12、GPIO13 的启动电平和休眠行为做一次板级确认。

## 5. 来源说明

本结论基于以下代码位置人工梳理：

- /home/ats/git-code/151_l3/main/app_power.c
- /home/ats/git-code/151_l3/main/app_use_btn.c
- /home/ats/git-code/151_l3/main/app_debug.c
- /home/ats/git-code/151_l3/main/main.c
- /home/ats/git-code/151_l3/modules/rs485/port/rs485_port_esp.c
- /home/ats/git-code/151_l3/components/at/at_port.c
- /home/ats/git-code/151_l3/components/at/dev_sidus_ble.c
- /home/ats/git-code/151_l3/components/dev_lamp/dev_lamp.c
- /home/ats/git-code/151_l3/components/dev_ws28xx/dev_ws28xx.c
- /home/ats/git-code/151_l3/components/dev_ws28xx/led_spi_strip_encoder.c
- /home/ats/git-code/151_l3/components/cmd_wifi/include/ambient_config.h
- /home/ats/git-code/151_l3/components/cmd_system/cmd_system_sleep.c

## 6. Aputure IP Project 移植后核对结果

以下结论是基于当前仓库实际代码与板级默认配置补充得到，用于区分“151_l3 上游事实”和“当前移植落地状态”。

### 6.1 已确认存在的问题

1. 151_l3 文档中的 ADC 校准通道与实际采样通道不一致问题，在当前仓库已额外修正。
	- 当前仓库音频 ADC 采样使用 `ADC_CHANNEL_7(GPIO8)`。
	- 当前仓库校准初始化也已切到 `ADC_CHANNEL_7(GPIO8)`。
	- 这意味着 GPIO3 在当前仓库中不再承载 ADC 校准角色，只保留给 RS485 DIR 使用。

### 6.2 当前仓库与 151_l3 一致的项

- RS485 TX/RX 仍为 GPIO9 / GPIO10。
- RS485 DIR 已回到 GPIO3，且不再与当前有效 ADC 路径重叠。
- 本地按键仍为 GPIO37。
- Ambient 灯带数据仍为 GPIO38。
- Ambient RGB 总使能仍为 GPIO48。
- WS28xx 第一段输出已对齐到 GPIO15。
- WS28xx 第二段输出仍为 GPIO16。
- Sidus BLE Reset 已对齐到 GPIO21。

### 6.3 建议处理顺序

1. 继续保留对 GPIO3 的约束，避免后续又把 ADC 校准或其他模拟输入功能重新挂回该脚。

当前仓库已经消除了 GPIO38 的双重占用；本文档可作为“151_l3 上游引脚基线 + 当前仓库落地结果”共同使用。需要额外注意的是，当前仓库在 ADC 校准一致性上已经比 151_l3 更完整，不应再回退到 `ADC_CHANNEL_2(GPIO3)` 的旧配置。