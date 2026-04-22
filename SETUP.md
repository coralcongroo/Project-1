# MQTT Server & Monitor 快速开始

## 📋 系统要求

- Python 3.10+
- mosquitto 2.x（MQTT Broker）
- paho-mqtt >= 1.6.1

### 安装依赖

```bash
# 安装 mosquitto（Ubuntu/Debian）
sudo apt install mosquitto

# 安装 Python 依赖
pip install -r requirements.txt
```

---

## 🚀 一键自动调试

运行自动调试脚本，可自动完成以下操作：
- ✅ 检查系统依赖
- ✅ 启动 MQTT Server（双端口配置）
- ✅ 连接监控客户端
- ✅ 初始化示例设备台账
- ✅ 模拟设备并测试命令下发
- ✅ 输出配置和测试报告

### 运行命令

```bash
python debug_setup.py
```

### 输出示例

```
============================================================
MQTT Server & Monitor 自动调试设置
============================================================

[步骤 1] 检查系统依赖
✓ mosquitto 已安装
✓ paho-mqtt 已安装

[步骤 2] 初始化 MQTT Server 配置
✓ MQTT Server 已启动 (port 8883 + local 1883)

[步骤 3] 验证 Server 监听
✓ 本地 1883 可连接
✓ 外网 8883 可连接

[步骤 4] 启动监控客户端
✓ 已连接到 127.0.0.1:1883，开始监听设备上报

[步骤 5] 初始化设备台账
✓ 已添加设备: 112233aabbcc (DEV001)
✓ 已添加设备: aabbccdd1122 (DEV002)

[步骤 6] 模拟设备并测试命令下发
✓ 命令已发布
✓ 命令发布
✓ 设备接收

[步骤 7] 测试报告
✓ 命令下发测试通过
✓ 设备管理测试通过

✓ 自动调试设置完成！所有测试通过
============================================================
```

---

## 🎮 使用 Streamlit UI

自动调试完成后，启动 Web UI：

```bash
python -m streamlit run ui_app.py
```

在浏览器中打开 **http://localhost:8501**

### MQTT 功能标签页

#### 1️⃣ **Server 控制**
- 配置监听地址、端口、TLS、ACL
- 启动/停止/重启 MQTT Server
- 查看服务器日志

#### 2️⃣ **监控连接 & 消息**
- 连接到 Broker（127.0.0.1:1883）
- 实时查看 TX/RX 消息流水
- 显示在线客户端统计

#### 3️⃣ **在线设备**
- 列出所有已注册设备及在线状态
- 显示最后上报时间和内容
- 一键将所有设备标记离线

#### 4️⃣ **命令下发**
- 单一设备/群组/全体下发命令
- 预设命令模板（开灯、关灯、亮度调节等）
- 批量发布多个 MAC 地址

#### 5️⃣ **设备台账**
- 添加/删除/编辑设备
- CSV 批量导入
- 导出为 JSON

---

## 📁 文件结构

```
Project-1/
├── mqtt_server.py          # MQTT Server 管理（mosquitto 启停、配置）
├── mqtt_monitor.py         # MQTT 监控客户端（订阅、上报、台账管理）
├── ui_app.py               # Streamlit Web UI
├── debug_setup.py          # 一键自动调试脚本
├── requirements.txt        # Python 依赖
│
├── .mqtt_server/           # 工作目录
│   ├── mosquitto.conf      # mosquitto 配置文件
│   ├── mosquitto.log       # mosquitto 日志
│   ├── mosquitto.acl       # ACL 文件（可选）
│   └── devices.json        # 设备台账（自动生成）
│
├── deploy/
│   └── emqx/               # EMQX 部署模板
└── README.md               # 本文件
```

---

## 🔧 配置详解

### Server 配置（MqttServerConfig）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `listener_host` | `0.0.0.0` | Server 监听地址 |
| `listener_port` | `8883` | Server 监听端口 |
| `allow_anonymous` | `False` | 是否允许匿名连接 |
| `tls_enabled` | `True` | 是否启用 TLS/SSL |
| `local_plain_port` | `1883` | 本地监控端口（无 TLS） |
| `password_file` | `` | 密码文件路径 |
| `acl_file` | `` | ACL 文件路径 |

### 设备上报主题

| 主题 | 说明 |
|------|------|
| `report/data` | 设备状态上报 |
| `iot/device/{mac}/timer_reply` | 定时任务回复 |
| `report/{type}` | 其他上报类型 |

### 命令下发主题

| 主题 | 说明 |
|------|------|
| `iot/device/{mac}/down` | 单一设备下发 |
| `iot/device/{mac}/timer` | 定时任务下发 |
| `iot/device/group/down` | 群组下发 |
| `iot/device/all/down` | 全体下发 |

---

## 🧪 测试场景

### 场景 1：模拟设备上报

```json
// Publish to: report/data
{
  "mac": "112233aabbcc",
  "status": "online",
  "power": true,
  "lightness": 50
}
```

### 场景 2：下发灯光命令

```json
// Publish to: iot/device/112233aabbcc/down
{
  "power": true,
  "lightness": 75,
  "cct": 5000
}
```

### 场景 3：批量下发

- 在「命令下发」标签 → 批量发布
- 输入多个 MAC（每行一个）
- 选择主题模板（用 `{mac}` 占位）
- 点击「批量发布」

---

## 🐛 常见问题

### Q1: 启动失败 — "Address already in use"
**解决**: 前一个 mosquitto 进程还在运行
```bash
pkill -9 mosquitto
python debug_setup.py
```

### Q2: 监控客户端连接失败
**解决**: 检查 mosquitto 是否在监听 1883
```bash
ss -tlnp | grep 1883
```

### Q3: 设备没有收到命令
**可能原因**:
- 设备还未订阅相应主题 → 等待设备完全连接
- 主题拼写错误 → 检查 MAC 是否正确
- ACL 限制 → 确保 ACL 规则允许该客户端

---

## 📊 架构图

```
┌─────────────────────────────────────────────────────────┐
│                 Streamlit Web UI                        │
│  (ui_app.py)                                            │
└─────────────────────────────────────────────────────────┘
           ↓                              ↓
┌──────────────────────┐    ┌───────────────────────┐
│  MQTT Server Manager │    │   MQTT Monitor        │
│  (mqtt_server.py)    │    │   (mqtt_monitor.py)   │
│                      │    │                       │
│ - Start/Stop         │    │ - Connect/Disconnect  │
│ - Config Gen         │    │ - Subscribe Topics    │
│ - ACL Gen            │    │ - Message Recording   │
│ - Log Tail           │    │ - Device Registry     │
└──────────────────────┘    └───────────────────────┘
           ↓                              ↓
       mosquitto (8883 + 1883)
           ↓
    ┌──────────────────┐
    │  MQTT Devices    │
    │  (Real/Simulated)│
    └──────────────────┘
```

---

## 📝 日志位置

- **Server 日志**: `.mqtt_server/mosquitto.log`
- **设备台账**: `.mqtt_server/devices.json`
- **Streamlit 输出**: 终端 stdout

### 查看实时日志

```bash
tail -f .mqtt_server/mosquitto.log
```

---

## 🔐 安全建议

> ⚠️ 当前配置是**开发调试模式**（无 TLS、允许匿名）

生产环境请：
1. **启用 TLS** — 提供 CA/证书/密钥文件
2. **设置密码认证** — 生成 password_file
3. **配置 ACL** — 限制每个设备的主题权限
4. **改变默认端口** — 不使用 1883/8883

详见 [server.md](server.md) 和 [deploy/emqx/](deploy/emqx/)

---

## 📞 技术支持

有问题？检查以下文件：
- [server.md](server.md) — MQTT Server 规范
- [mqtt_monitor.py](mqtt_monitor.py) — 监控客户端源码注释
- [mqtt_server.py](mqtt_server.py) — Server 管理源码注释
- `.mqtt_server/mosquitto.log` — 运行日志
