# EMQX 部署落地（按 server.md）

本目录用于把 [server.md](server.md) 的规则转成可执行配置模板。

## 1. 监听/TLS 建议

- 端口: `8883`
- TLS: `TLSv1.2+`
- 禁止匿名: `true`
- 证书文件:
  - `ca.crt`
  - `server.crt`
  - `server.key`

参考模板: [listeners_tls_template.conf](listeners_tls_template.conf)

## 2. ACL 规则模板

参考: [acl_semantic_template.txt](acl_semantic_template.txt)

按每个设备的 `mac` 生成：

- allow subscribe: `iot/device/{mac}/down`
- allow subscribe: `iot/device/{mac}/timer`
- allow subscribe: `iot/device/group/down`
- allow subscribe: `iot/device/group/timer`
- allow subscribe: `iot/device/all/down`
- allow subscribe: `iot/device/all/timer`
- allow publish: `report/data`
- allow publish: `iot/device/{mac}/timer_reply`

## 3. 设备台账模板

参考: [device_registry_template.csv](device_registry_template.csv)

衍生规则:

- `client_id = aputure-{mac}`
- `topic_down = iot/device/{mac}/down`
- `topic_timer = iot/device/{mac}/timer`
- `topic_timer_reply = iot/device/{mac}/timer_reply`
