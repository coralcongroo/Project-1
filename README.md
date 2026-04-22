# Project-1

基于 Aputure IP 网络协议要求实现的上位机控制器与最小 SDK。

## 文件说明

- [controller.py](controller.py): 协议控制器（MQTT / UDP5569 / UDP5568 AMBL / BLE TLV与CRC）
- [sdk.py](sdk.py): 业务友好的 SDK 封装（任务ID生成、任务映射、统一调用）
- [example.py](example.py): 最小可用示例
- [example_batch.py](example_batch.py): 批量创建/删除倒计时示例
- [all_feature_examples.py](all_feature_examples.py): 各功能完整示例合集
- [cli.py](cli.py): 命令行控制器（联调/脚本集成）
- [ui_app.py](ui_app.py): Web UI 控制面板（Streamlit）
- [device_manager.py](device_manager.py): 设备列表管理（扫描结果导入/导出）
- [requirements.txt](requirements.txt): Python 依赖

## 快速开始

1. 安装依赖
	- `pip install -r requirements.txt`
2. 修改 [example.py](example.py) 中的 `mac` 与 `device_ip`
3. 运行示例
	- `python example.py`

## UI 界面

1. 安装依赖
	- `pip install -r requirements.txt`
2. 启动 UI
	- `streamlit run ui_app.py`
3. 浏览器打开后可使用以下标签页：
	- 灯光控制（MQTT）
	- 倒计时（MQTT/UDP）
	- AMBL 实时流
	- BLE 编码（TLV/CRC）
	- 批量任务（SDK）
	- 主动扫描（UDP5569）+ 设备列表管理

## 已覆盖能力

- MQTT: 灯光控制、倒计时命令、`timer_reply` 回执等待
- UDP 5569: 倒计时命令 JSON 请求/响应、超时重试
- UDP 5568: AMBL 二进制实时帧发送
- BLE: 倒计时 TLV 编码与 CRC16(0xA001)

## 新增增强

- MQTT 自动重连：指数退避（默认 1s ~ 30s）
- MQTT 连接超时控制：默认 8 秒
- 统一异常模型：参数校验、连接异常、命令超时、设备执行失败
- 主动扫描：按 CIDR 并发探测 UDP5569 返回设备清单
- 设备列表管理：保存/加载扫描结果到 JSON（含追加、删除、重命名、MAC 更新）

## 批量能力

`AputureSDK` 新增：

- `batch_create_timers(items, transport, retries, retry_delay, rollback_on_error)`
	- 支持批量创建
	- 单任务失败可自动重试
	- 可选失败后回滚已创建任务
- `batch_remove_timers(task_ids, transport, retries, retry_delay)`
	- 支持批量删除
	- 返回 `ok` 或 `partial`（含失败明细）

## 各功能示例索引

见 [all_feature_examples.py](all_feature_examples.py)：

- `example_mqtt_light_control()`：MQTT 灯光控制
- `example_mqtt_timer_commands()`：MQTT 倒计时 6 指令
- `example_udp_timer_commands()`：UDP 5569 倒计时命令
- `example_ambl_realtime_stream()`：UDP 5568 AMBL 实时流
- `example_ble_tlv_and_crc()`：BLE TLV 与 CRC16
- `example_sdk_basic()`：SDK 基础调用
- `example_sdk_batch()`：SDK 批量与回滚

## CLI 快速示例（覆盖各功能）

- MQTT 灯光控制
	- `python cli.py light --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --power true --mode cct --lightness 70 --cct 4500`
- MQTT 倒计时 add/query/list/stats/remove/clear
	- `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport mqtt add --task-id 101 --type once --trigger-time 2026-04-21T23:00:00 --power true --mode cct --lightness 75 --cct 4300`
	- `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport mqtt query --task-id 101`
	- `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport mqtt list`
	- `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport mqtt stats`
	- `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport mqtt remove --task-id 101`
	- `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport mqtt clear`
- UDP 5569 倒计时命令
	- `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport udp add --task-id 201 --type once --trigger-time 2026-04-21T23:30:00 --power true --mode cct --lightness 65 --cct 5000`
- UDP 5568 AMBL 实时流
	- `python cli.py ambl --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --sequence 1 --channels 4 --r 255 --g 0 --b 0 --a 255`
- BLE TLV/CRC 编码
	- `python cli.py ble-encode --type weekly --trigger-time 2026-04-21T20:10:05 --weekday 2 --power true --mode cct --lightness 50 --cct 4200`
- SDK 批量创建（重试+回滚）
	- `python cli.py batch-add --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport mqtt --type once --trigger-times 2026-04-21T23:00:00 2026-04-21T23:05:00 2026-04-21T23:10:00 --power true --mode cct --lightness 60 --cct 4300 --retries 2 --retry-delay 0.3`
- 主动扫描（UDP5569）
	- `python cli.py scan --cidr 192.168.1.0/24 --cmd stats_timer --timeout 0.35 --workers 64`
	- `python cli.py scan --cidr 192.168.1.0/24 --save devices.json` （扫描并保存）