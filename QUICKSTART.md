# 🚀 MQTT Server & Monitor 快速入门

## 📦 一分钟快速开始

```bash
# 1. 检查环境（可选）
python check_env.py

# 2. 一键自动调试（启动 Server + 监控 + 测试）
python debug_setup.py

# 3. 启动 Web UI（默认 http://localhost:8501）
python -m streamlit run ui_app.py
```

**完成！** 现在可以在 Web UI 中进行命令下发和设备监控。

---

## 🎯 常用命令

### 使用 Make（推荐）

```bash
# 一键调试
make setup

# 启动 UI
make ui

# 查看日志
make logs

# 停止 Server
make kill

# 查看所有命令
make help
```

### 使用 Python

```bash
# 环境检查
python check_env.py

# 自动调试
python debug_setup.py

# 启动 UI
python -m streamlit run ui_app.py
```

---

## 🖥️ Web UI 使用指南

### 访问地址
```
http://localhost:8501
```

### 5 大功能标签

| 标签 | 功能 |
|------|------|
| **🖥 Server 控制** | 启停 mosquitto、配置参数、查看日志 |
| **📡 监控连接 & 消息** | 连接 Broker、实时消息流水、在线统计 |
| **🟢 在线设备** | 设备列表、在线状态、最后上报时间 |
| **📤 命令下发** | 单个/批量发送 MQTT 命令 |
| **📋 设备台账** | 添加/编辑/导入导出设备 |

---

## 🧪 测试示例

### 示例 1: 发送开灯命令

1. 打开 **🖥 Server 控制** → 点击「启动 Server」
2. 打开 **📡 监控连接 & 消息**
   - Broker 地址: `127.0.0.1`
   - 端口: `1883`
   - 点击「连接监控」
3. 打开 **📤 命令下发**
   - MAC: `112233aabbcc`
   - 主题预设: `个别下发 iot/device/112233aabbcc/down`
   - Payload 预设: `开灯 power=true`
   - 点击「发布命令」
4. 查看 **📡 监控连接 & 消息** 中的消息记录

### 示例 2: 导入设备

1. 打开 **📋 设备台账**
2. 在「从 CSV 批量导入」区域：
   ```
   mac,device_sn,firmware_ver,group_id,remark
   112233aabbcc,DEV001,v1.0,group1,示例设备
   aabbccdd1122,DEV002,v1.0,group2,另一个设备
   ```
3. 点击「导入 CSV」
4. 刷新页面查看设备列表

### 示例 3: 批量发送命令

1. 打开 **📤 命令下发** → 向下滚动到「批量发布」
2. MAC 列表：
   ```
   112233aabbcc
   aabbccdd1122
   ```
3. 主题模板: `iot/device/{mac}/down`
4. Payload: `{"power":true}`
5. 点击「批量发布」

---

## 📊 生成的文件

`debug_setup.py` 运行后会生成：

```
.mqtt_server/
├── mosquitto.conf          # Server 配置文件
├── mosquitto.log           # Server 运行日志
├── mosquitto.acl           # ACL 规则（可选）
└── devices.json            # 设备台账

示例 devices.json:
{
  "112233aabbcc": {
    "mac": "112233aabbcc",
    "client_id": "aputure-112233aabbcc",
    "status": "online",
    "last_seen": "2026-04-22 16:33:34",
    "device_sn": "DEV001",
    "firmware_ver": "v1.0",
    "group_id": "group1",
    "remark": "示例设备"
  },
  ...
}
```

---

## 🔌 实际设备连接

### 设备端代码示例（Python）

```python
import paho.mqtt.client as mqtt
import json

def on_connect(client, userdata, flags, rc):
    print(f"Connected with rc: {rc}")
    # 订阅命令下发主题
    client.subscribe("iot/device/112233aabbcc/down", qos=1)

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    print(f"收到命令: {payload}")
    
    # 执行命令（例如控制灯光）
    if payload.get("power"):
        print("开灯")
    else:
        print("关灯")
    
    # 上报执行结果
    report = json.dumps({
        "mac": "112233aabbcc",
        "status": "ok",
        "power": payload.get("power", False)
    })
    client.publish("report/data", report, qos=1)

# 连接到 Broker
client = mqtt.Client(client_id="aputure-112233aabbcc")
client.on_connect = on_connect
client.on_message = on_message
client.connect("192.168.1.1", 1883)  # 改为实际 Server 地址
client.loop_forever()
```

### 关键点

- **Client ID**: 必须为 `aputure-{mac}` 格式
- **订阅主题**: 
  - `iot/device/{mac}/down` — 个别命令
  - `iot/device/group/down` — 群组命令
  - `iot/device/all/down` — 全体命令
- **上报主题**: `report/data`

---

## ⚙️ 配置参数

### Server 配置

在 **🖥 Server 控制** 中可配置：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 监听地址 | `0.0.0.0` | Server 绑定地址 |
| 监听端口 | `8883` | Server 端口 |
| 本地裸连端口 | `1883` | 本机监控端口（无 TLS） |
| 允许匿名 | ✓ | 是否允许不认证连接 |
| 启用 TLS | ✗（开发模式） | 是否启用 SSL/TLS |

### 文件位置

所有配置和数据存储在 `.mqtt_server/` 目录下。

---

## 🐛 故障排查

### 问题 1: "Address already in use"

**原因**: 前一个 mosquitto 进程还在运行

**解决**:
```bash
pkill -9 mosquitto
python debug_setup.py
```

### 问题 2: "监控连接失败"

**原因**: mosquitto 没有在 1883 监听

**检查**:
```bash
ss -tlnp | grep 1883
```

**解决**: 在 UI 中重新启动 Server，确保「本地裸连端口」设为 1883

### 问题 3: "设备收不到命令"

**可能原因**:
1. 主题拼写错误 → 检查 MAC 地址
2. 设备未订阅 → 设备还在连接过程中
3. ACL 限制 → 关闭 ACL 或修改规则

**调试**:
```bash
# 查看 mosquitto 日志
tail -100f .mqtt_server/mosquitto.log | grep "112233aabbcc"
```

---

## 📚 完整文档

- [SETUP.md](SETUP.md) — 详细安装和配置指南
- [server.md](server.md) — MQTT Server 规范
- [mqtt_server.py](mqtt_server.py) — Server 管理器源码
- [mqtt_monitor.py](mqtt_monitor.py) — 监控客户端源码
- [ui_app.py](ui_app.py) — Web UI 源码

---

## 🎓 架构说明

```
┌──────────────────────────────────────────────┐
│        Streamlit Web UI                      │
│        (ui_app.py)                           │
└──────┬────────────────────────────┬──────────┘
       │                            │
       ▼                            ▼
┌─────────────────────┐     ┌───────────────────┐
│  MqttServerManager   │     │  MqttMonitor      │
│  (mqtt_server.py)   │     │  (mqtt_monitor.py)│
└──────┬──────────────┘     └────────┬──────────┘
       │                            │
       │   Subprocess               │ paho-mqtt
       ▼                            ▼
  ┌──────────────────────────────────────┐
  │    mosquitto (MQTT Broker)           │
  │    Port 8883 + 1883                  │
  └──────────────────────────────────────┘
       ▲                            ▲
       │                            │
       └────┬─────────────┬─────────┘
            │             │
     ┌──────▼──┐   ┌──────▼──┐
     │ Device  │   │  Device  │
     │  (Real) │   │(Simulated)
     └─────────┘   └──────────┘
```

---

## 💡 最佳实践

1. **开发调试** — 使用当前配置（无 TLS、匿名连接）
2. **局域网部署** — 启用 ACL，添加密码认证
3. **生产环境** — 启用 TLS、CA 证书、强密码、严格 ACL

详见 [server.md](server.md)

---

## 📞 获取帮助

1. 检查日志: `tail -f .mqtt_server/mosquitto.log`
2. 运行诊断: `python check_env.py`
3. 查看代码注释: 各 `.py` 文件都有详细注释
4. 参考完整文档: [SETUP.md](SETUP.md)

---

**祝你使用愉快！** 🎉
