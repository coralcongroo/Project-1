# MQTT 运维交付模板 (EMQX)

更新时间: 2026-04-22
适用范围: Aputure_IP_Project 设备接入与运维上线

## 1. 交付目标

本模板用于服务器同事快速完成以下事项:

- EMQX TLS 监听与证书配置
- 设备账号与 ACL 授权
- 设备 MAC 到 ClientId/Topic 的登记管理
- 上线前连通性与权限验证

## 2. 设备接入规则 (固定)

- ClientId 规则: aputure-{mac}
- MAC 规则: 12 位小写十六进制，无冒号
- 设备下行 Topic:
  - iot/device/{mac}/down
  - iot/device/{mac}/timer
  - iot/device/group/down
  - iot/device/group/timer
  - iot/device/all/down
  - iot/device/all/timer
- 设备上行 Topic:
  - report/data
  - iot/device/{mac}/timer_reply

示例 (mac=112233aabbcc):

- ClientId: aputure-112233aabbcc
- 订阅: iot/device/112233aabbcc/down
- 订阅: iot/device/112233aabbcc/timer
- 发布: iot/device/112233aabbcc/timer_reply

## 3. TLS/CA 配置模板

### 3.1 证书准备清单

- 服务器证书: server.crt
- 服务器私钥: server.key
- CA 链: ca.crt (需与设备侧内嵌 CA 链匹配)

设备侧当前使用内嵌 CA 文件:

- components/network/mqtt_agent/certs/emq_root_ca.pem

如 Broker CA 更新，需同步替换设备侧 emq_root_ca.pem 并重新发布固件。

### 3.2 EMQX TLS 监听建议

- 监听端口: 8883
- 最低 TLS 版本: TLSv1.2
- 禁止匿名接入: 开启认证
- 证书链完整性: 必须包含中间证书（若有）

建议在 EMQX Dashboard 中按以下项核对:

- Listener: mqtt:ssl:default
- Bind: 0.0.0.0:8883
- SSL enable: true
- CA file / cert file / key file 路径正确

## 4. ACL 授权模板

下面给出“规则模板”，可映射到 EMQX 的 File ACL 或 Dashboard ACL。

### 4.1 每设备最小权限

允许订阅:

- iot/device/{mac}/down
- iot/device/{mac}/timer
- iot/device/group/down
- iot/device/group/timer
- iot/device/all/down
- iot/device/all/timer

允许发布:

- report/data
- iot/device/{mac}/timer_reply

拒绝:

- 其他所有 Topic

### 4.2 ACL 规则示例 (语义示例)

```text
# subject: clientid = aputure-112233aabbcc
allow subscribe iot/device/112233aabbcc/down
allow subscribe iot/device/112233aabbcc/timer
allow subscribe iot/device/group/down
allow subscribe iot/device/group/timer
allow subscribe iot/device/all/down
allow subscribe iot/device/all/timer
allow publish   report/data
allow publish   iot/device/112233aabbcc/timer_reply
deny  all
```

说明:

- 上述为“权限语义模板”，落地时请按你们 EMQX 版本对应的 ACL 语法填写。
- 若使用 Dashboard ACL，可直接按主题与动作逐条配置。

## 5. 设备登记模板

建议维护设备台账 (CSV/Excel/数据库)，字段如下:

| 字段 | 示例 | 说明 |
|---|---|---|
| device_sn | AP-0001 | 设备序列号 |
| mac | 112233aabbcc | 小写12位hex |
| client_id | aputure-112233aabbcc | 固定规则生成 |
| topic_down | iot/device/112233aabbcc/down | 设备控制下行 |
| topic_timer | iot/device/112233aabbcc/timer | 倒计时下行 |
| topic_timer_reply | iot/device/112233aabbcc/timer_reply | 倒计时回执 |
| group_id | group | 群组标识 |
| firmware_ver | v1.0.x | 固件版本 |
| ca_version | emq-root-2026Q2 | 证书版本 |
| status | active | 激活状态 |

建议派生规则:

- client_id = "aputure-" + mac
- topic_down = "iot/device/" + mac + "/down"
- topic_timer = "iot/device/" + mac + "/timer"
- topic_timer_reply = "iot/device/" + mac + "/timer_reply"

## 6. 上线验收步骤

### 6.1 Broker 验收

- 8883 端口可达
- TLS 证书链有效
- 认证开启
- ACL 生效

### 6.2 设备验收

检查设备日志包含:

- MQTT client_id=aputure-{mac}
- MQTT device down topic=iot/device/{mac}/down
- MQTT device timer topic=iot/device/{mac}/timer
- MQTT device timer reply topic=iot/device/{mac}/timer_reply
- MQTT connected

### 6.3 命令验收

1) 灯光控制:

- 向 iot/device/{mac}/down 发布最小控制包
- 验证设备动作与状态上报 report/data

2) 倒计时控制:

- 向 iot/device/{mac}/timer 发布 add_timer
- 验证回执 topic iot/device/{mac}/timer_reply

3) 权限验证:

- 尝试向非授权 topic 发布/订阅，确保被拒绝

## 7. 常见故障定位

### 7.1 TLS 握手失败

排查顺序:

1. 服务器证书是否过期
2. 证书链是否完整
3. 设备内嵌 CA 是否与 Broker CA 匹配
4. 若开启 CN 校验，Broker 域名与证书 CN/SAN 是否一致

### 7.2 连上 Broker 但无消息

排查顺序:

1. ClientId 是否与设备 MAC 规则一致
2. Topic 是否大小写/格式正确
3. ACL 是否缺少对应 publish/subscribe 权限
4. 消息 QoS 与 retain 设置是否符合预期

### 7.3 定时器回执收不到

排查顺序:

1. 是否订阅 iot/device/{mac}/timer_reply
2. add_timer 载荷字段是否完整 (cmd/task_id/type/trigger_time + 至少一个状态字段)
3. 设备日志是否出现 invalid payload/no state fields

## 8. 变更管理建议

任何以下变更都需要执行“服务器 + 设备”双侧联动发布:

- Broker 域名/端口变更
- 证书链变更
- Topic 模板变更
- ClientId 前缀变更

建议每次变更记录:

- 变更单号
- 生效时间
- 影响设备范围
- 回滚方案

---

附注: 本模板是运维交付文档，不替代工程协议文档。协议字段与行为以 docs/MQTT_UDP_PROTOCOL_SPEC.md 为准。