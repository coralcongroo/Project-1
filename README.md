# Project-1

基于 Aputure 协议的控制工具集（当前为 **MQTT Server 模式**）。

> 已移除 MQTT 客户端业务（不再由本项目作为 MQTT client 进行 publish/subscribe）。

## 主要文件

- [controller.py](controller.py): 协议控制（UDP5569 / UDP5568 AMBL / BLE）
- [mqtt_server.py](mqtt_server.py): MQTT Server 进程管理（mosquitto）
- [ui_app.py](ui_app.py): Streamlit UI（含 MQTT Server 管理页）
- [sdk.py](sdk.py): SDK（默认 UDP）
- [cli.py](cli.py): CLI（UDP/AMBL/BLE/扫描）
- [device_manager.py](device_manager.py): 扫描结果设备列表管理
- [deploy/emqx/README_EMQX_DEPLOY.md](deploy/emqx/README_EMQX_DEPLOY.md): 按 server.md 生成的 EMQX 落地模板

## 环境准备

1. 创建虚拟环境
   - `python3 -m venv .venv
   - `source .venv/bin/activate`
2. 安装 Python 依赖
   - `pip install -r requirements.txt`
3. 安装 MQTT Broker（Linux）
   - `sudo apt install mosquitto`

## 启动 UI

- `python -m streamlit run ui_app.py`

标签页：
- MQTT：仅 Server 管理（启动/停止/重启/日志/监听检测）
- UDP：倒计时、AMBL、主动扫描
- BLE：TLV/CRC 编码
- 设备管理：批量设备操作（UDP）

MQTT 页面已按 server.md 增加：
- TLS 配置项（CA/证书/私钥）
- ACL 文件路径
- 按 `mac` 批量生成 ACL（`ClientId = aputure-{mac}`）

## CLI 示例（Server 模式）

- UDP 倒计时 add
  - `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport udp add --task-id 201 --type once --trigger-time 2026-04-21T23:30:00 --power true --mode cct --lightness 65 --cct 5000`
- UDP 倒计时 query/list/stats/remove/clear
  - `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport udp query --task-id 201`
  - `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport udp list`
  - `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport udp stats`
  - `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport udp remove --task-id 201`
  - `python cli.py timer --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --transport udp clear`
- AMBL
  - `python cli.py ambl --mac 11:22:33:aa:bb:cc --device-ip 192.168.1.100 --sequence 1 --channels 4 --r 255 --g 0 --b 0 --a 255`
- BLE 编码
  - `python cli.py ble-encode --type weekly --trigger-time 2026-04-21T20:10:05 --weekday 2 --power true --mode cct --lightness 50 --cct 4200`
- 扫描
  - `python cli.py scan --cidr 192.168.1.0/24 --save devices.json`

## 说明

- SDK 默认 `transport="udp"`。
- 若调用 MQTT 客户端相关接口，将抛出“Server 模式已禁用”异常。