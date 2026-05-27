# Aputure IP Project - MQTT/UDP 通讯协议说明

更新时间: 2026-04-22  
适用版本: 当前主干代码 (ESP-IDF 5.4.1)

## 1. 文档目的

本文档用于上位机/云端平台对接本工程的 MQTT 与 UDP 通讯能力，覆盖:

- MQTT 灯光控制与倒计时任务控制
- UDP 倒计时 JSON 命令口
- UDP 实时灯效流 (AMBL 二进制)

说明以当前代码实现为准。

补充说明:

- UDP/MQTT 二进制 proto 控制链现已按 [protocols/proto/AputureDeviceReference.proto](../../protocols/proto/AputureDeviceReference.proto) 的 `Envelope` 通信。
- 当前控制语义仍以 `RawBleControl.packets` 为主，每个元素对应一个完整 BLE mesh/GATT 包。
- 旧 `Message.proto` 帧只保留接收兼容，不再作为新的上位机对接格式。

## 2. MQTT 协议

### 2.1 连接参数

- Broker URI: mqtts://broker.emqx.io:8883 (默认)
- 传输安全: TLS
- Client ID 规则: {prefix}-{mac}
  - 默认 prefix: aputure
  - mac: 12 位小写十六进制，例如 112233aabbcc
- QoS: 订阅/发布均使用 QoS1
- 自动重连: 启用
- 账号密码: 支持，可为空

### 2.2 Topic 规划

设备标识符定义:

- device id: 设备 MAC (小写，无冒号)
- group id: group
- all id: all

灯光控制下行 Topic:

- iot/device/{device_id}/down
- iot/device/{group_id}/down
- iot/device/{all_id}/down

倒计时下行 Topic:

- iot/device/{device_id}/timer
- iot/device/{group_id}/timer
- iot/device/{all_id}/timer

倒计时回执 Topic:

- iot/device/{device_id}/timer_reply

状态上报 Topic:

- report/data

### 2.3 灯光控制报文 (down)

请求格式: JSON，字段可部分下发。

字段定义:

- power: bool 或 number，0/1
- mode: cct | hsi | xy
- level: 0..254
- lightness: 0..100
- cct: uint16 (建议 2700..6500)
- gm: float
- hue: 0..360
- sat: 0..100
- x: 0..1
- y: 0..1

示例:

```json
{
  "power": true,
  "mode": "cct",
  "lightness": 80,
  "cct": 5600
}
```

设备处理规则:

- 仅包含合法字段才会生效
- hue/sat 下发会切换到 hsi 模式
- x/y 下发会切换到 xy 模式
- level 与 lightness 会进行互相换算
- 越界值会做钳位处理

### 2.4 倒计时控制报文 (timer)

命令集合:

- add_timer
- remove_timer
- clear_timer
- query_timer
- list_timer
- stats_timer

#### 2.4.1 add_timer

请求示例:

```json
{
  "cmd": "add_timer",
  "task_id": 101,
  "type": "once",
  "trigger_time": "2026-04-22T23:00:00",
  "power": true,
  "mode": "cct",
  "lightness": 75,
  "cct": 4500
}
```

字段约束:

- task_id: uint32，建议全局唯一
- type: once | daily | weekly 或 0/1/2
- trigger_time: 支持以下格式
  - YYYY-MM-DDTHH:MM:SS
  - YYYY-MM-DD HH:MM:SS
- 至少包含一个状态字段 (power/mode/level/lightness/cct/gm/hue/sat/x/y)

#### 2.4.2 remove_timer

```json
{
  "cmd": "remove_timer",
  "task_id": 101
}
```

#### 2.4.3 clear_timer

```json
{
  "cmd": "clear_timer"
}
```

#### 2.4.4 query_timer

```json
{
  "cmd": "query_timer",
  "task_id": 101
}
```

#### 2.4.5 list_timer

```json
{
  "cmd": "list_timer"
}
```

#### 2.4.6 stats_timer

```json
{
  "cmd": "stats_timer"
}
```

### 2.5 timer_reply 回执格式

回执统一在 iot/device/{device_id}/timer_reply 返回。

通用字段:

- action: 对应命令名
- result: ok | error
- message: 可选，错误信息或状态说明
- task_id: 可选

add/query 成功示例:

```json
{
  "action": "add_timer",
  "result": "ok",
  "task": {
    "task_id": 101,
    "type": "once",
    "status": "pending",
    "trigger_time": "2026-04-22T23:00:00",
    "created_ts_ms": 1713798000000,
    "last_executed_ts_ms": 0,
    "target_state": {
      "power": true,
      "mode": "cct",
      "lightness": 75,
      "cct": 4500
    }
  }
}
```

list 成功示例:

```json
{
  "action": "list_timer",
  "result": "ok",
  "count": 2,
  "tasks": [
    {
      "task_id": 101,
      "type": "once",
      "status": "pending",
      "trigger_time": "2026-04-22T23:00:00"
    },
    {
      "task_id": 102,
      "type": "daily",
      "status": "pending",
      "trigger_time": "2026-04-22T07:30:00"
    }
  ]
}
```

stats 成功示例:

```json
{
  "action": "stats_timer",
  "result": "ok",
  "executed": 5,
  "pending": 2,
  "cancelled": 1,
  "total": 8
}
```

失败示例:

```json
{
  "action": "add_timer",
  "result": "error",
  "message": "invalid payload",
  "task_id": 101
}
```

### 2.6 MQTT 上位机实现建议

- 订阅至少包含:
  - report/data
  - iot/device/{device_id}/timer_reply
- 下发 timer 命令后以 timer_reply 的 action/result 作为最终结果
- 单次业务超时建议 3~5 秒
- 若 result=error 且 message 为参数问题，不要盲重试，先修正 payload

## 3. UDP 倒计时命令协议 (JSON)

### 3.1 传输参数

- 协议: UDP
- 目标地址: 设备 IPv4 单播地址
- 端口: 5569 (默认)
- 最大请求负载: 1024 字节
- 交互模式: 请求-响应 (单包)

### 3.2 命令与字段

UDP 命令集合、字段定义、请求示例、返回结构与 MQTT timer 完全一致:

- add_timer
- remove_timer
- clear_timer
- query_timer
- list_timer
- stats_timer

返回也是 JSON，并包含 action/result/message/task_id/task/count/tasks 等字段。

### 3.3 UDP 请求示例

```json
{
  "cmd": "query_timer",
  "task_id": 101
}
```

对应响应示例:

```json
{
  "action": "query_timer",
  "result": "ok",
  "task": {
    "task_id": 101,
    "type": "once",
    "status": "pending",
    "trigger_time": "2026-04-22T23:00:00"
  }
}
```

### 3.4 UDP 上位机实现建议

- 超时建议: 1~2 秒
- 丢包重试: 最多 2 次
- task_id 建议使用递增或雪花 ID，避免重复覆盖

## 4. UDP Proto 二进制命令协议

### 4.1 传输参数

- 协议: UDP
- 目标地址: 设备 IPv4 单播地址
- 端口: 5569 (默认)
- 报文格式: `AputureDeviceReference.proto` 的 `Envelope`

### 4.2 当前已启用消息

- `DISCOVERY_REQUEST(1001)` -> 设备回 `DEVICE_INFO(1002)`
- `HEARTBEAT(1003)` -> 设备回 `HEARTBEAT(1003)`
- `RAW_BLE_CONTROL(1201)` -> 设备遍历 `RawBleControl.packets` 并桥接到 BLE 控制路径

### 4.3 当前控制语义

- 现阶段 UDP proto 控制仍不是 typed light state 直控
- 当前活跃控制路径为 `RawBleControl.packets -> app_bluetooth_handle_mesh_packet()`
- 如果需要 typed `StateSetRequest`/`StateReport`，应作为后续迁移，不应假定当前设备端已经启用

## 5. UDP 实时灯效流协议 (AMBL 二进制)

该通道用于局域网低延迟连续灯效数据传输，和 UDP 5569 命令口并行存在。

### 4.1 传输参数

- 协议: UDP 组播
- 组播地址: 239.255.23.42
- 端口: 5568
- 最大帧长: 2048 字节
- 最大通道数: 500
- 帧超时: 200ms (设备会标记流失效)

### 4.2 帧格式

固定头 (24 字节，网络字节序):

- magic: uint32 = 0x414D424C
- version: uint16 = 1
- header_size: uint16 = 24
- sequence: uint32
- payload_size: uint16
- channel_count: uint16
- timestamp_us: uint64

负载:

- RGBA 字节流
- 约束: payload_size == channel_count * 4

设备校验规则:

- magic/version/header_size 不匹配，丢弃
- 长度不匹配，丢弃
- channel_count 超过最大值，丢弃
- 校验失败无回包

## 6. 倒计时任务能力边界

- 最大并发任务数: 16 (默认)
- 队列长度: 10 (默认)
- 扫描精度: 1 秒
- 持久化: NVS 保存，重启恢复

任务类型:

- once: 单次执行
- daily: 每日执行
- weekly: 每周执行 (0=周日..6=周六)

## 6. 错误处理约定

业务错误常见 message:

- missing cmd
- missing task_id
- invalid json
- invalid payload
- no state fields
- unsupported cmd
- ESP_ERR_* (设备内部错误名)

上位机处理建议:

1. 参数错误: 立即修正请求，不重试
2. 超时或网络错误: 可重试 1~2 次
3. 多次失败: 标记设备离线并触发健康检查

## 7. 联调建议

建议顺序:

1) 先打通 UDP 5569 的 add/query/list  
2) 再打通 MQTT timer 与 timer_reply  
3) 最后接入 UDP 5568 实时流

推荐使用现有工具:

- tools/udp_countdown_test.py
- tools/ble_countdown_test.py (如需同时联调 BLE 倒计时)

## 8. 版本建议

建议上位机保存以下可配置项，避免固件升级造成硬编码耦合:

- broker URI
- topic format
- UDP command port
- UDP multicast address/port
- 协议版本号与回退策略

---

如需，我可以继续补一份上位机 SDK 数据结构模板 (Python/TypeScript)，直接把本文字段映射成可调用接口。