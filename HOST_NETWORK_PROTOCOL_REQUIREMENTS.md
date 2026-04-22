# Aputure IP 工程 - 上位机网络协议要求说明

更新时间: 2026-04-21
适用对象: 上位机/网关/自动化平台开发人员

## 1. 目标与范围

本说明用于指导上位机对接本工程当前已实现的网络协议能力，覆盖以下链路:

- MQTT 控制与状态上报
- UDP 倒计时命令口 (JSON)
- UDP 实时灯效流 (二进制 AMBL)
- BLE 倒计时分片协议 (Mesh Vendor 扩展)

说明基于当前代码实现，不包含历史已删除或未落地接口。

## 2. 连接与通道总览

- 设备网络前提: 设备已入网并获得 IPv4 地址
- MQTT Broker 默认地址: mqtts://broker.emqx.io:8883
- UDP 实时流地址: 239.255.23.42:5568
- UDP 倒计时命令口: 设备IP:5569
- BLE: 10 字节 Mesh Vendor 数据帧，支持倒计时任务分片下发

## 3. MQTT 协议要求

### 3.1 主题规则

设备使用 Wi-Fi STA MAC (小写十六进制无分隔符) 构建主题，例如 MAC=112233aabbcc。

下行控制主题:

- iot/device/{mac}/down
- iot/device/group/down
- iot/device/all/down

倒计时下行主题:

- iot/device/{mac}/timer
- iot/device/group/timer
- iot/device/all/timer

倒计时回执主题:

- iot/device/{mac}/timer_reply

状态上报主题:

- report/data

### 3.2 MQTT 连接参数

- 协议: TLS MQTT (mqtts)
- 默认 QoS: 1
- 自动重连: 启用
- ClientId 规则: {prefix}-{mac}，默认 prefix=aputure
- 用户名/密码: 支持，可为空

### 3.3 灯光控制 JSON 字段

下发到 down 主题的 JSON 可包含以下字段 (可部分更新):

- power: bool 或 number，0/1
- mode: cct | hsi | xy
- level: 0..254
- lightness: 0..100
- cct: 色温数值
- gm: 绿色-洋红偏移
- hue: 0..360
- sat: 0..100
- x: 0..1
- y: 0..1

行为约束:

- lightness 会同步换算为 matter level
- hue/sat 会自动切换为 hsi 模式
- x/y 会自动切换为 xy 模式
- 越界值会被设备侧钳位

### 3.4 倒计时 MQTT JSON 命令

下发主题: iot/device/{mac}/timer (或 group/all)

支持命令:

- add_timer
- remove_timer
- clear_timer
- query_timer
- list_timer
- stats_timer

add_timer 请求示例:

```json
{
  "cmd": "add_timer",
  "task_id": 101,
  "type": "once",
  "trigger_time": "2026-04-21T23:00:00",
  "power": true,
  "mode": "cct",
  "lightness": 75,
  "cct": 4500
}
```

remove_timer 请求示例:

```json
{
  "cmd": "remove_timer",
  "task_id": 101
}
```

回执统一格式:

- 成功简报: action/result/message/task_id
- 任务详情: action/result/task
- 列表: action=list_timer, result=ok, count, tasks[]
- 统计: action=stats_timer, result=ok, executed/pending/cancelled/total

失败场景常见 message:

- invalid payload
- missing task_id
- no state fields
- queue failed
- ESP_ERR_* 名称字符串

## 4. UDP 倒计时命令口 (JSON)

### 4.1 传输要求

- 协议: UDP
- 目标: 设备单播 IP
- 端口: 5569 (默认)
- 最大 JSON 负载: 1024 字节
- 请求/响应模式: 单包请求，单包 JSON 回包

### 4.2 命令集合

与 MQTT timer 命令一致:

- add_timer
- remove_timer
- clear_timer
- query_timer
- list_timer
- stats_timer

字段语义与 MQTT 相同。

### 4.3 时间字段要求

trigger_time 接受以下格式:

- YYYY-MM-DDTHH:MM:SS
- YYYY-MM-DD HH:MM:SS

type 支持:

- once
- daily
- weekly

也支持数字:

- 0=once
- 1=daily
- 2=weekly

## 5. 倒计时任务模型要求

- task_id: uint32，建议由上位机全局唯一分配
- 最大并发任务数: 16 (默认)
- 队列深度: 10 (默认)
- 检查周期: 1 秒
- 持久化: NVS，重启后恢复

任务类型约束:

- once: 依赖完整年月日时分秒
- daily: 使用时分秒
- weekly: 使用星期(0=周日..6=周六) + 时分秒

## 6. UDP 实时灯效流 (AMBL 二进制)

用于低延迟高频灯效输出，和倒计时 JSON 命令口互不冲突。

### 6.1 传输参数

- 目标地址: 239.255.23.42:5568
- 协议: UDP 组播
- 最大帧长: 2048 字节
- 最大通道数: 500
- 帧超时: 200ms (超时后输出标记 stale)

### 6.2 帧结构

头部固定 24 字节，网络字节序:

- magic: uint32 = 0x414D424C
- version: uint16 = 1
- header_size: uint16 = 24
- sequence: uint32
- payload_size: uint16
- channel_count: uint16
- timestamp_us: uint64

payload:

- RGBA 连续数组
- 长度必须满足 payload_size = channel_count * 4

设备侧校验失败将丢包，不回包。

## 7. BLE 倒计时分片协议要求

BLE 为 Vendor 扩展 10 字节包，倒计时采用 BEGIN/CHUNK/COMMIT/ABORT 机制。

### 7.1 帧类型

- BEGIN = 0x30
- CHUNK = 0x31
- COMMIT = 0x32
- ABORT = 0x33

定时器类型:

- ONCE=0
- DAILY=1
- WEEKLY=2

会话约束:

- 最大并发 session: 2
- 超时回收: 默认 3 秒
- TLV 最大长度: 128 字节

### 7.2 TLV 字段定义

时间类:

- 0x01 TIME_ABS: 7字节 [year_hi year_lo mon day hour min sec]
- 0x02 TIME_HMS: 3字节 [hour min sec]
- 0x03 WEEKDAY: 1字节 [0..6]

状态类:

- 0x10 POWER: 1字节 [0/1]
- 0x11 MODE: 1字节 [0=cct 1=hsi 2=xy]
- 0x12 LEVEL: 1字节 [0..254]
- 0x13 LIGHTNESS_X10: u16, 实值=raw/10
- 0x14 CCT: u16
- 0x15 GM_X100: s16, 实值=raw/100
- 0x16 HUE_X10: u16, 实值=raw/10
- 0x17 SAT_X10: u16, 实值=raw/10
- 0x18 X_X10000: u16, 实值=raw/10000
- 0x19 Y_X10000: u16, 实值=raw/10000

### 7.3 CRC 与顺序

- 分片顺序必须严格递增
- COMMIT 的 CRC16 校验多项式: 0xA001
- seq/total 不匹配、CRC 错误、session 无效都会导致提交失败

建议上位机直接复用工具脚本的编码策略:

- tools/ble_countdown_test.py

## 8. 统一状态字段语义

上位机应遵守以下状态字段语义，避免跨协议行为不一致:

- power: 开关主状态
- mode: 决定 lightness 写入哪个颜色子结构
- level 与 lightness: 建议二选一发送，避免自相矛盾
- cct/gm: 主要用于 cct 模式，hsi 模式下 cct/gm 也可存在
- hue/sat: 发送后设备切换到 hsi
- x/y: 发送后设备切换到 xy

## 9. 错误处理与重试策略 (上位机建议)

### 9.1 MQTT

- 连接异常: 指数退避重连 (1s, 2s, 4s...上限30s)
- 业务命令: 以 timer_reply 为准判定成功
- 建议设置业务超时: 3~5 秒

### 9.2 UDP 命令口

- 单次请求超时建议: 1~2 秒
- 未收到回包时建议重试 2 次
- 若出现 invalid payload/no state fields，应立即修正参数而非盲重试

### 9.3 BLE

- BEGIN 后若 CHUNK 超时，建议发送 ABORT 并重开 session
- COMMIT 失败时，完整重发该任务所有分片

## 10. 版本与兼容性建议

- 上位机应维护 protocol_version，并在配置中可切换 topic/端口
- 对未知字段应忽略，不应导致解析失败
- 对关键字段缺失应本地拦截，避免发到设备后才失败

## 11. 最小可用对接清单

上位机至少应实现:

- MQTT 连接、订阅与发布
- UDP 5569 命令发送与回包解析
- add/remove/query/list/stats/clear 六个倒计时命令
- task_id 生成策略与本地映射
- 错误码与超时重试机制

建议增强:

- UDP 5568 AMBL 实时流发送
- BLE 分片发送器 (可直接参考脚本)
- 设备时间同步状态检查 (避免 once 任务错时)

## 12. 联调建议

推荐联调顺序:

1) 先打通 UDP 5569 add/query/list
2) 再打通 MQTT timer + timer_reply
3) 最后接 BLE 分片下发
4) 完成后压测: 连续 16 任务、重启恢复、并发修改

可直接使用现有脚本辅助:

- tools/udp_countdown_test.py
- tools/ble_countdown_test.py

---

如需我继续，我可以在这份说明基础上再给你补一版“上位机接口定义 (Python/TypeScript 数据模型 + SDK 示例调用)”。
