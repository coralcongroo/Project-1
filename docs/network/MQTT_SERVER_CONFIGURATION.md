# MQTT 服务器配置文档

更新时间: 2026-04-22
适用工程: Aputure_IP_Project

## 1. 目的

本文档用于说明当前工程的 MQTT 连接配置，重点包含:

- Broker 地址与协议版本
- TLS 与 CA 证书配置
- 设备 MAC 到 ClientId 与 Topic 的映射规则
- 服务器端 ACL/订阅建议

## 2. 设备侧 MQTT 固定配置

配置来源: 工程 Kconfig 默认值

- MQTT 开关: CONFIG_AP_MQTT_ENABLE=y
- Broker URI: mqtts://broker.emqx.io:8883
- 协议版本: MQTT v3.1.1 (默认，未启用 v5)
- TLS 开关: CONFIG_AP_MQTT_ENABLE_TLS (默认开启)
- 自动重连: 启用
- QoS: 订阅与发布均使用 QoS1
- 用户名: 空字符串 (可配置)
- 密码: 空字符串 (可配置)
- ClientId 前缀: aputure
- 跳过证书 CN 校验: 启用
- 使用内嵌 EMQX Root CA: 启用

## 3. CA 证书配置

### 3.1 当前 CA 来源

设备使用内嵌文本证书 certs/emq_root_ca.pem，编译时通过 EMBED_TXTFILES 打包进固件。

关键点:

- 证书文件: components/network/mqtt_agent/certs/emq_root_ca.pem
- 构建嵌入: components/network/mqtt_agent/CMakeLists.txt
- 运行时绑定: components/network/mqtt_agent/src/mqtt_agent.c

运行时将证书地址与长度赋给 mqtt_cfg.broker.verification.certificate 与 certificate_len。

### 3.2 CA 更换流程

1. 替换证书文件内容:
   components/network/mqtt_agent/certs/emq_root_ca.pem
2. 保持 CMake 中 EMBED_TXTFILES 条目不变
3. 重新编译固件并烧录
4. 用 monitor 检查 MQTT 握手是否成功

### 3.3 安全建议

当前配置启用了 skip_cert_common_name_check。生产环境建议关闭该项，并确保 Broker 证书 CN/SAN 与服务器地址匹配。

### 3.4 关闭 TLS 选项

已新增配置项:

- CONFIG_AP_MQTT_ENABLE_TLS

配置路径:

- idf.py menuconfig
- Project Configuration
- MQTT Agent
- Enable MQTT TLS (mqtts)

行为说明:

- 开启 TLS: 使用 CONFIG_AP_MQTT_BROKER_URI 原值 (通常 mqtts://...)
- 关闭 TLS: 若 URI 以 mqtts:// 开头，设备会自动转换为 mqtt:// 后连接
- 关闭 TLS 时将跳过证书相关配置

## 4. MAC 地址与 ClientId/Topic 映射

### 4.1 MAC 来源

设备在启动时读取 Wi-Fi STA MAC (esp_read_mac with ESP_MAC_WIFI_STA)。

### 4.2 格式规则

- MAC 格式: 12 位小写十六进制，无分隔符
- 示例 MAC: 112233aabbcc

### 4.3 ClientId 规则

- ClientId = {CONFIG_AP_MQTT_CLIENT_ID_PREFIX}-{mac}
- 示例: aputure-112233aabbcc

### 4.4 Topic 映射规则

设 mac=112233aabbcc，group=group，all=all:

控制下行:

- iot/device/112233aabbcc/down
- iot/device/group/down
- iot/device/all/down

倒计时下行:

- iot/device/112233aabbcc/timer
- iot/device/group/timer
- iot/device/all/timer

倒计时回执:

- iot/device/112233aabbcc/timer_reply

状态上报:

- report/data

## 5. 服务器端配置要求

## 5.1 监听与协议

- 开启 8883 TLS 监听
- 支持 MQTT v3.1.1
- QoS1 消息收发
- 保持会话与自动重连兼容

### 5.2 ACL 建议

建议按设备 MAC 粒度做授权:

设备订阅权限:

- iot/device/{mac}/down
- iot/device/group/down
- iot/device/all/down
- iot/device/{mac}/timer
- iot/device/group/timer
- iot/device/all/timer

设备发布权限:

- report/data
- iot/device/{mac}/timer_reply

如需更严格隔离，可禁止设备订阅 report/data，仅保留专用下行 topic。

### 5.3 鉴权建议

当前工程用户名密码默认空。若生产启用鉴权:

- 配置 AP_MQTT_USERNAME 与 AP_MQTT_PASSWORD
- Broker 侧绑定 client_id 或 topic ACL
- 建议结合设备证书或 token 做二次校验

## 6. 设备上线自检信息

设备初始化 MQTT 时会打印关键日志，可用于运维登记:

- MQTT client_id=...
- MQTT report topic=...
- MQTT device down topic=...
- MQTT device timer topic=...
- MQTT device timer reply topic=...
- MQTT agent started, broker=...

建议上位机首次配对时记录以下信息:

- 设备 MAC
- MQTT ClientId
- 设备专属下行 Topic
- 设备专属 timer_reply Topic
- 固件版本与配置快照

## 7. 配置项速查

- Broker URI: CONFIG_AP_MQTT_BROKER_URI
- 协议版本: CONFIG_AP_MQTT_USE_V5 (默认关闭)
- 用户名: CONFIG_AP_MQTT_USERNAME
- 密码: CONFIG_AP_MQTT_PASSWORD
- ClientId 前缀: CONFIG_AP_MQTT_CLIENT_ID_PREFIX
- 状态上报 Topic: CONFIG_AP_MQTT_REPORT_TOPIC
- 下行 Topic 模板: CONFIG_AP_MQTT_DEVICE_DOWN_TOPIC_FMT
- timer Topic 模板: CONFIG_AP_MQTT_DEVICE_TIMER_TOPIC_FMT
- timer_reply 模板: CONFIG_AP_MQTT_DEVICE_TIMER_REPLY_TOPIC_FMT
- 证书 CN 校验开关: CONFIG_AP_MQTT_SKIP_CERT_COMMON_NAME_CHECK
- 内嵌 CA 开关: CONFIG_AP_MQTT_USE_EMQX_ROOT_CA

## 8. 推荐联调步骤

1. 先确认 Broker TLS 正常，客户端可连接 8883
2. 上电设备，记录日志中的 client_id 与 topic
3. 向 iot/device/{mac}/down 下发最小控制包，确认设备响应
4. 向 iot/device/{mac}/timer 下发 add_timer，确认 timer_reply 回执
5. 断网恢复，确认自动重连与订阅恢复

## 9. 运维交付模板

如需交付服务器/运维团队，请配合使用:

- docs/network/MQTT_EMQX_OPS_TEMPLATE.md

---

附: 本文档基于当前工程代码与配置生成，若修改 Kconfig 或 mqtt_agent 逻辑，请同步更新本文档。