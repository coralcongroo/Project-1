from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import streamlit as st  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover
    raise SystemExit("请先安装依赖: pip install -r requirements.txt") from exc

from controller import AputureController, ControllerConfig
from sdk import AputureSDK, DeviceCommandError, LightState
from device_manager import DeviceListManager
from batch_controller import BatchDeviceController
from mqtt_server import MqttServerConfig, MqttServerManager
from mqtt_monitor import MqttMonitor


def _default_cidr_from_ip(ip: str) -> str:
    parts = ip.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return "192.168.1.0/24"


def _get_server_manager() -> MqttServerManager:
    if "mqtt_server_manager" not in st.session_state:
        workspace = Path(__file__).resolve().parent / ".mqtt_server"
        st.session_state.mqtt_server_manager = MqttServerManager(str(workspace))
    return st.session_state.mqtt_server_manager


def _get_monitor() -> MqttMonitor:
    if "mqtt_monitor" not in st.session_state:
        store = Path(__file__).resolve().parent / ".mqtt_server" / "devices.json"
        st.session_state.mqtt_monitor = MqttMonitor(str(store))
    return st.session_state.mqtt_monitor


def show_mqtt_status_panel(cfg: ControllerConfig) -> None:
    st.sidebar.subheader("MQTT Server 状态")
    mgr = _get_server_manager()

    st.sidebar.write(f"进程状态: {mgr.status_text()}")
    ok, msg = mgr.check_listener(cfg.mqtt_host, int(cfg.mqtt_port))
    if ok:
        st.sidebar.success(f"监听检测: {msg}")
    else:
        st.sidebar.warning(f"监听检测: {msg}")


def show_mqtt_dialog_tab(cfg: ControllerConfig) -> None:
    st.subheader("MQTT 对话框（Server 管理 + 监控）")
    mgr = _get_server_manager()
    mon = _get_monitor()

    # ── 功能子标签 ──────────────────────────────────────────────────
    sub_server, sub_monitor, sub_devices, sub_cmd, sub_registry = st.tabs([
        "🖥 Server 控制",
        "📡 监控连接 & 消息",
        "🟢 在线设备",
        "📤 命令下发",
        "📋 设备台账",
    ])

    # ================================================================
    # 子标签 1: Server 控制
    # ================================================================
    with sub_server:
        st.markdown("**服务器日志**")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            refresh = st.button("刷新日志", key="mqtt_server_refresh")
        with c2:
            if st.button("清空日志", key="mqtt_server_clear_log"):
                mgr.log_path.write_text("", encoding="utf-8")
                st.info("已清空日志")
        with c3:
            max_lines = st.number_input(
                "显示行数", min_value=20, max_value=1000, value=200, step=20, key="mqtt_server_log_lines"
            )

        if refresh or True:
            logs = mgr.tail_logs(max_lines=int(max_lines))
            st.text_area(
                "Server Logs", value=logs or "(暂无日志)", height=260, key="mqtt_server_log_text"
            )

        st.markdown("**Server 参数**")
        listener_host = st.text_input("监听地址", value=cfg.mqtt_host, key="mqtt_server_host")
        listener_port = st.number_input(
            "监听端口", min_value=1, max_value=65535, value=int(cfg.mqtt_port), step=1, key="mqtt_server_port"
        )
        allow_anonymous = st.checkbox("允许匿名连接", value=False, key="mqtt_server_allow_anon")
        password_file = st.text_input("密码文件（可选）", value="", key="mqtt_server_password_file")
        acl_file = st.text_input(
            "ACL 文件（可选）",
            value=str(mgr.workspace / "mosquitto.acl"),
            key="mqtt_server_acl_file",
        )

        st.markdown("**TLS 配置（建议 server.md 规范：8883 + TLSv1.2）**")
        tls_enabled = st.checkbox("启用 TLS", value=True, key="mqtt_server_tls_enabled")
        cafile = st.text_input("CA 文件", value="/etc/emqx/certs/ca.crt", key="mqtt_server_cafile")
        certfile = st.text_input("服务端证书", value="/etc/emqx/certs/server.crt", key="mqtt_server_certfile")
        keyfile = st.text_input("服务端私钥", value="/etc/emqx/certs/server.key", key="mqtt_server_keyfile")
        local_plain_port = st.number_input(
            "本地裸连端口（内部监控用，0=不开启）",
            min_value=0, max_value=65535, value=1883, step=1,
            help="TLS 启用时，额外在 127.0.0.1 开启此端口供本机监控客户端免 TLS 连接",
            key="mqtt_server_local_plain_port",
        )

        st.markdown("**设备 ACL 生成（ClientId: aputure-{mac}）**")
        mac_lines = st.text_area(
            "MAC 列表（每行一个，12位hex或带冒号）",
            value="112233aabbcc",
            height=100,
            key="mqtt_server_mac_list",
        )
        if st.button("生成 ACL 文件", key="mqtt_server_gen_acl"):
            macs = [x.strip() for x in mac_lines.splitlines() if x.strip()]
            target = mgr.write_acl_from_macs(macs, out_path=acl_file if acl_file.strip() else None)
            st.success(f"ACL 已生成: {target}")

        def _build_server_cfg() -> MqttServerConfig:
            return MqttServerConfig(
                listener_host=listener_host,
                listener_port=int(listener_port),
                allow_anonymous=allow_anonymous,
                password_file=password_file,
                acl_file=acl_file,
                tls_enabled=tls_enabled,
                cafile=cafile,
                certfile=certfile,
                keyfile=keyfile,
                local_plain_port=int(local_plain_port),
            )

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            if st.button("启动 Server", key="mqtt_server_start"):
                ok, msg = mgr.start(_build_server_cfg())
                st.success(msg) if ok else st.error(msg)
        with s2:
            if st.button("停止 Server", key="mqtt_server_stop"):
                ok, msg = mgr.stop()
                st.info(msg) if ok else st.error(msg)
        with s3:
            if st.button("重启 Server", key="mqtt_server_restart"):
                mgr.stop()
                ok, msg = mgr.start(_build_server_cfg())
                st.success(msg) if ok else st.error(msg)
        with s4:
            if st.button("检测监听", key="mqtt_server_probe"):
                ok, msg = mgr.check_listener(listener_host, int(listener_port))
                st.success(msg) if ok else st.warning(msg)

        st.caption(f"当前状态: {mgr.status_text()}")

        st.markdown("**预设参数**")
        p1, p2, p3 = st.columns(3)
        with p1:
            if st.button("本机调试 127.0.0.1:1883", key="mqtt_server_preset_local"):
                st.session_state.mqtt_server_host = "127.0.0.1"
                st.session_state.mqtt_server_port = 1883
                st.rerun()
        with p2:
            if st.button("局域网 0.0.0.0:1883", key="mqtt_server_preset_lan"):
                st.session_state.mqtt_server_host = "0.0.0.0"
                st.session_state.mqtt_server_port = 1883
                st.rerun()
        with p3:
            if st.button("MQTTS 0.0.0.0:8883", key="mqtt_server_preset_mqtts"):
                st.session_state.mqtt_server_host = "0.0.0.0"
                st.session_state.mqtt_server_port = 8883
                st.rerun()

    # ================================================================
    # 子标签 2: 监控连接 & 消息记录
    # ================================================================
    with sub_monitor:
        st.markdown("**监控客户端连接（订阅设备上报）**")
        m_host = st.text_input("Broker 地址", value="127.0.0.1", key="mon_host")
        m_port = st.number_input("Broker 端口", min_value=1, max_value=65535, value=1883, step=1, key="mon_port")
        m_user = st.text_input("用户名（可选）", value="", key="mon_user")
        m_pass = st.text_input("密码（可选）", value="", type="password", key="mon_pass")
        m_tls = st.checkbox("启用 TLS", value=False, key="mon_tls")

        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            if st.button("连接监控", key="mon_connect"):
                ok, msg = mon.connect(
                    host=m_host,
                    port=int(m_port),
                    username=m_user,
                    password=m_pass,
                    use_tls=m_tls,
                )
                st.success(msg) if ok else st.error(msg)
        with mc2:
            if st.button("断开监控", key="mon_disconnect"):
                ok, msg = mon.disconnect()
                st.info(msg) if ok else st.error(msg)
        with mc3:
            if st.button("测试连通性", key="mon_ping"):
                ok, msg = mon.connect(
                    host=m_host, port=int(m_port), username=m_user,
                    password=m_pass, use_tls=m_tls, timeout_s=2.0,
                )
                if ok:
                    st.success(f"✅ Broker 可连接: {msg}")
                    # 若只是测试，立刻断开
                else:
                    st.error(f"❌ 无法连接: {msg}")

        st.caption(f"监控状态: {mon.status_text()}")
        st.caption(f"$SYS 统计: 在线客户端={mon.sys_stats.get('broker/clients/connected', '?')}  "
                   f"总连接={mon.sys_stats.get('broker/clients/total', '?')}")

        st.divider()
        st.markdown("**消息记录（TX / RX）**")
        msg_limit = st.number_input("显示条数", min_value=10, max_value=500, value=50, step=10, key="mon_msg_limit")
        if st.button("刷新消息", key="mon_refresh_msgs"):
            pass  # 触发重渲染

        msgs = mon.get_messages(int(msg_limit))
        if msgs:
            rows = [
                {
                    "时间": m.ts,
                    "方向": "⬆ TX" if m.direction == "tx" else "⬇ RX",
                    "主题": m.topic,
                    "内容": m.payload[:120] + ("..." if len(m.payload) > 120 else ""),
                }
                for m in msgs
            ]
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("暂无消息，请先连接监控客户端并等待设备上报")

        if st.button("清空消息记录", key="mon_clear_msgs"):
            mon.messages.clear()
            st.info("消息记录已清空")

    # ================================================================
    # 子标签 3: 在线设备
    # ================================================================
    with sub_devices:
        st.markdown("**在线设备列表**")
        col_r, col_mo = st.columns([1, 1])
        with col_r:
            if st.button("刷新", key="dev_refresh"):
                pass
        with col_mo:
            if st.button("全部标记离线", key="dev_all_offline"):
                mon.mark_all_offline()
                st.info("已将所有设备标记为离线")

        devices = mon.get_devices()
        if devices:
            rows = [
                {
                    "MAC": r.mac,
                    "ClientId": r.client_id,
                    "状态": "🟢 在线" if r.status == "online" else "⚫ 离线",
                    "最后在线": r.last_seen,
                    "固件": r.firmware_ver,
                    "分组": r.group_id,
                    "备注": r.remark,
                    "最近上报": r.last_report[:60] + ("..." if len(r.last_report) > 60 else ""),
                }
                for r in devices
            ]
            st.dataframe(rows, use_container_width=True)
            st.caption(f"共 {len(devices)} 台设备，其中在线 {mon.get_online_count()} 台")
        else:
            st.info("设备台账为空，连接监控后设备上报消息时会自动入库，也可在「设备台账」手动添加")

    # ================================================================
    # 子标签 4: 命令下发
    # ================================================================
    with sub_cmd:
        st.markdown("**向设备发布 MQTT 命令**")
        st.caption("按 server.md/HOST_NETWORK_PROTOCOL_REQUIREMENTS.md：灯光走 /down，倒计时走 /timer（必须带 cmd 字段）")

        devices_list = mon.get_devices()
        mac_options = [r.mac for r in devices_list] if devices_list else []

        # 目标 MAC 选择
        cmd_target_mode = st.radio(
            "目标设备", options=["手动输入", "从台账选择"], horizontal=True, key="cmd_target_mode"
        )
        if cmd_target_mode == "从台账选择" and mac_options:
            cmd_mac = st.selectbox("选择 MAC", options=mac_options, key="cmd_mac_select")
        else:
            cmd_mac = st.text_input("MAC（12位hex）", value="112233aabbcc", key="cmd_mac_input")

        cmd_mac_clean = str(cmd_mac).replace(":", "").replace("-", "").lower()

        # 预设主题
        preset_topics = {
            "自定义": "",
            f"个别下发 iot/device/{cmd_mac_clean}/down": f"iot/device/{cmd_mac_clean}/down",
            f"定时下发 iot/device/{cmd_mac_clean}/timer": f"iot/device/{cmd_mac_clean}/timer",
            "群组下发 iot/device/group/down": "iot/device/group/down",
            "全体下发 iot/device/all/down": "iot/device/all/down",
        }
        topic_preset = st.selectbox("主题预设", options=list(preset_topics.keys()), key="cmd_topic_preset")
        default_topic = preset_topics[topic_preset] or f"iot/device/{cmd_mac_clean}/down"
        if "cmd_topic_last_preset" not in st.session_state:
            st.session_state.cmd_topic_last_preset = topic_preset
            if "cmd_topic" not in st.session_state:
                st.session_state.cmd_topic = default_topic
        if topic_preset != st.session_state.cmd_topic_last_preset and topic_preset != "自定义":
            st.session_state.cmd_topic = default_topic
        st.session_state.cmd_topic_last_preset = topic_preset
        cmd_topic = st.text_input("发布主题", value=default_topic, key="cmd_topic")

        # 预设命令 payload
        preset_payloads = {
            "自定义": "",
            "开灯 power=true": '{"power":true}',
            "关灯 power=false": '{"power":false}',
            "亮度 50%": '{"lightness":50.0}',
            "定时-添加(add_timer)": (
                '{"cmd":"add_timer","task_id":101,"type":"once",'
                '"trigger_time":"2026-04-21T23:00:00","power":true,"lightness":75}'
            ),
            "定时-移除(remove_timer)": '{"cmd":"remove_timer","task_id":101}',
            "定时-查询(query_timer)": '{"cmd":"query_timer","task_id":101}',
            "定时-列表(list_timer)": '{"cmd":"list_timer"}',
            "定时-统计(stats_timer)": '{"cmd":"stats_timer"}',
            "定时-清空(clear_timer)": '{"cmd":"clear_timer"}',
        }
        payload_preset = st.selectbox("Payload 预设", options=list(preset_payloads.keys()), key="cmd_payload_preset")
        default_payload = preset_payloads[payload_preset] if preset_payloads[payload_preset] else '{"power":true}'
        if "cmd_payload_last_preset" not in st.session_state:
            st.session_state.cmd_payload_last_preset = payload_preset
            if "cmd_payload" not in st.session_state:
                st.session_state.cmd_payload = default_payload
        if payload_preset != st.session_state.cmd_payload_last_preset and payload_preset != "自定义":
            st.session_state.cmd_payload = default_payload
        st.session_state.cmd_payload_last_preset = payload_preset
        cmd_payload = st.text_area("Payload (JSON)", value=default_payload, height=100, key="cmd_payload")
        cmd_qos = st.selectbox("QoS", options=[0, 1, 2], index=1, key="cmd_qos")

        if st.button("发布命令", key="cmd_publish"):
            if not mon.is_connected():
                st.error("监控客户端未连接，请先在「监控连接」标签连接到 Broker")
            else:
                # JSON 有效性校验
                try:
                    parsed = json.loads(cmd_payload)
                except Exception as exc:
                    st.error(f"Payload 不是合法 JSON: {exc}")
                    parsed = None

                if parsed is not None and not isinstance(parsed, dict):
                    st.error("Payload 必须是 JSON 对象")
                elif parsed is not None:
                    is_timer_topic = str(cmd_topic).strip().endswith("/timer")
                    if is_timer_topic:
                        cmd = str(parsed.get("cmd", "")).strip()
                        valid_cmds = {
                            "add_timer", "remove_timer", "clear_timer", "query_timer", "list_timer", "stats_timer"
                        }
                        if cmd not in valid_cmds:
                            st.error("/timer 主题必须包含 cmd，且只能是: add_timer/remove_timer/clear_timer/query_timer/list_timer/stats_timer")
                        elif cmd == "add_timer":
                            required = ["task_id", "type", "trigger_time"]
                            missing = [k for k in required if k not in parsed]
                            state_keys = {"power", "mode", "level", "lightness", "cct", "gm", "hue", "sat", "x", "y"}
                            has_state = any(k in parsed for k in state_keys)
                            if missing:
                                st.error(f"add_timer 缺少字段: {', '.join(missing)}")
                            elif not has_state:
                                st.error("add_timer 至少包含一个状态字段: power/mode/level/lightness/cct/gm/hue/sat/x/y")
                            else:
                                ok, msg = mon.publish(cmd_topic, cmd_payload, qos=int(cmd_qos))
                                st.success(msg) if ok else st.error(msg)
                        else:
                            ok, msg = mon.publish(cmd_topic, cmd_payload, qos=int(cmd_qos))
                            st.success(msg) if ok else st.error(msg)
                    else:
                        ok, msg = mon.publish(cmd_topic, cmd_payload, qos=int(cmd_qos))
                        st.success(msg) if ok else st.error(msg)

        st.divider()
        st.markdown("**批量发布（逐 MAC 下发）**")
        batch_macs_raw = st.text_area(
            "MAC 列表（每行一个）", value="\n".join(mac_options[:5]) if mac_options else "112233aabbcc", height=100, key="cmd_batch_macs"
        )
        batch_topic_tpl = st.text_input(
            "主题模板（用 {mac} 占位）", value="iot/device/{mac}/down", key="cmd_batch_topic_tpl"
        )
        batch_payload = st.text_area("Payload", value='{"power":true}', height=80, key="cmd_batch_payload")
        if st.button("批量发布", key="cmd_batch_publish"):
            if not mon.is_connected():
                st.error("监控客户端未连接")
            else:
                batch_macs = [x.strip() for x in batch_macs_raw.splitlines() if x.strip()]
                results = []
                for bm in batch_macs:
                    bm_clean = bm.replace(":", "").replace("-", "").lower()
                    topic = batch_topic_tpl.replace("{mac}", bm_clean)
                    ok, msg = mon.publish(topic, batch_payload, qos=1)
                    results.append({"mac": bm_clean, "topic": topic, "ok": ok, "msg": msg})
                st.json(results)

    # ================================================================
    # 子标签 5: 设备台账
    # ================================================================
    with sub_registry:
        st.markdown("**设备台账管理**（入库、编辑、删除）")

        devices = mon.get_devices()
        if devices:
            rows = [
                {
                    "MAC": r.mac,
                    "ClientId": r.client_id,
                    "SN": r.device_sn,
                    "固件": r.firmware_ver,
                    "分组": r.group_id,
                    "备注": r.remark,
                    "状态": r.status,
                    "最后在线": r.last_seen,
                }
                for r in devices
            ]
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("台账为空")

        st.divider()
        st.markdown("**添加 / 更新设备**")
        reg_mac = st.text_input("MAC（必填，12位hex或带冒号）", value="112233aabbcc", key="reg_mac")
        reg_sn = st.text_input("设备 SN", value="", key="reg_sn")
        reg_fw = st.text_input("固件版本", value="", key="reg_fw")
        reg_group = st.text_input("分组 ID", value="", key="reg_group")
        reg_remark = st.text_input("备注", value="", key="reg_remark")

        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("保存设备", key="reg_save"):
                rec = mon.add_device(
                    mac=reg_mac,
                    device_sn=reg_sn,
                    firmware_ver=reg_fw,
                    group_id=reg_group,
                    remark=reg_remark,
                )
                st.success(f"已保存: {rec.client_id}")
                st.rerun()
        with rc2:
            if st.button("删除设备", key="reg_delete"):
                ok = mon.remove_device(reg_mac)
                st.success(f"已删除: {reg_mac}") if ok else st.warning("未找到该设备")
                st.rerun()

        st.divider()
        st.markdown("**从 CSV 批量导入**（列：mac, device_sn, firmware_ver, group_id, remark）")
        csv_content = st.text_area("CSV 内容（含表头）", height=120, key="reg_csv",
                                   value="mac,device_sn,firmware_ver,group_id,remark\n112233aabbcc,SN001,v1.0,group1,test")
        if st.button("导入 CSV", key="reg_csv_import"):
            import csv, io
            reader = csv.DictReader(io.StringIO(csv_content))
            count = 0
            for row in reader:
                mac = row.get("mac", "").strip()
                if not mac:
                    continue
                mon.add_device(
                    mac=mac,
                    device_sn=row.get("device_sn", "").strip(),
                    firmware_ver=row.get("firmware_ver", "").strip(),
                    group_id=row.get("group_id", "").strip(),
                    remark=row.get("remark", "").strip(),
                )
                count += 1
            st.success(f"已导入 {count} 条设备记录")
            st.rerun()

        st.divider()
        store_path = str(mon.store_path)
        st.caption(f"台账文件: {store_path}")
        if st.button("导出 JSON", key="reg_export"):
            data = {r.mac: r.__dict__ for r in mon.get_devices()}
            st.download_button(
                "下载 devices.json",
                data=json.dumps(data, ensure_ascii=False, indent=2),
                file_name="devices.json",
                mime="application/json",
                key="reg_download",
            )


def build_config() -> ControllerConfig:
    st.sidebar.header("设备配置")
    mac = st.sidebar.text_input("MAC", value="11:22:33:aa:bb:cc")
    device_ip = st.sidebar.text_input("设备 IP", value="192.168.1.100")
    mqtt_host = st.sidebar.text_input("MQTT Server 监听地址", value="0.0.0.0")
    mqtt_port = st.sidebar.number_input("MQTT Server 监听端口", min_value=1, max_value=65535, value=8883, step=1)

    return ControllerConfig(
        mac=mac,
        device_ip=device_ip,
        mqtt_host=mqtt_host,
        mqtt_port=int(mqtt_port),
    )


def build_state(prefix: str = "") -> Dict[str, Any]:
    power: Optional[bool]
    power_raw = st.selectbox(f"{prefix}power", options=["不发送", "true", "false"], index=0)
    if power_raw == "true":
        power = True
    elif power_raw == "false":
        power = False
    else:
        power = None

    mode = st.selectbox(f"{prefix}mode", options=["不发送", "cct", "hsi", "xy"], index=0)

    level = st.number_input(f"{prefix}level (0..254)", min_value=0, max_value=254, value=0, step=1)
    send_level = st.checkbox(f"{prefix}发送 level", value=False)

    lightness = st.number_input(f"{prefix}lightness (0..100)", min_value=0.0, max_value=100.0, value=50.0, step=1.0)
    send_lightness = st.checkbox(f"{prefix}发送 lightness", value=True)

    cct = st.number_input(f"{prefix}cct", min_value=1000, max_value=20000, value=4300, step=100)
    send_cct = st.checkbox(f"{prefix}发送 cct", value=False)

    gm = st.number_input(f"{prefix}gm", min_value=-100.0, max_value=100.0, value=0.0, step=0.1)
    send_gm = st.checkbox(f"{prefix}发送 gm", value=False)

    hue = st.number_input(f"{prefix}hue (0..360)", min_value=0.0, max_value=360.0, value=180.0, step=1.0)
    send_hue = st.checkbox(f"{prefix}发送 hue", value=False)

    sat = st.number_input(f"{prefix}sat (0..100)", min_value=0.0, max_value=100.0, value=80.0, step=1.0)
    send_sat = st.checkbox(f"{prefix}发送 sat", value=False)

    x = st.number_input(f"{prefix}x (0..1)", min_value=0.0, max_value=1.0, value=0.31, step=0.01, format="%.4f")
    send_x = st.checkbox(f"{prefix}发送 x", value=False)

    y = st.number_input(f"{prefix}y (0..1)", min_value=0.0, max_value=1.0, value=0.33, step=0.01, format="%.4f")
    send_y = st.checkbox(f"{prefix}发送 y", value=False)

    state: Dict[str, Any] = {}
    if power is not None:
        state["power"] = power
    if mode != "不发送":
        state["mode"] = mode
    if send_level:
        state["level"] = int(level)
    if send_lightness:
        state["lightness"] = float(lightness)
    if send_cct:
        state["cct"] = int(cct)
    if send_gm:
        state["gm"] = float(gm)
    if send_hue:
        state["hue"] = float(hue)
    if send_sat:
        state["sat"] = float(sat)
    if send_x:
        state["x"] = float(x)
    if send_y:
        state["y"] = float(y)
    return state


def show_light_tab(cfg: ControllerConfig) -> None:
    st.subheader("MQTT 灯光控制")
    st.warning("当前为 MQTT Server 模式，已禁用 MQTT 客户端控灯")


def show_timer_tab(cfg: ControllerConfig, fixed_transport: Optional[str] = None, key_prefix: str = "timer") -> None:
    st.subheader("倒计时命令")
    transport = "udp"
    st.caption("当前传输方式: UDP")

    operation = st.selectbox(
        "命令",
        options=["add", "remove", "query", "list", "stats", "clear"],
        key=f"{key_prefix}_operation",
    )

    task_id = st.number_input(
        "task_id",
        min_value=0,
        max_value=2**31 - 1,
        value=101,
        step=1,
        key=f"{key_prefix}_task_id",
    )
    timer_type = st.selectbox("type", options=["once", "daily", "weekly"], index=0, key=f"{key_prefix}_type")
    trigger_time = st.text_input("trigger_time", value="2026-04-21T23:00:00", key=f"{key_prefix}_trigger_time")

    state = build_state(f"{key_prefix}_定时_") if operation == "add" else {}

    if st.button("执行", key=f"{key_prefix}_run"):
        ctl = AputureController(cfg)
        try:
            if operation == "add":
                payload = {"task_id": int(task_id), "type": timer_type, "trigger_time": trigger_time, **state}
                result = ctl.send_timer_command_udp("add_timer", payload=payload)
            elif operation == "remove":
                result = ctl.send_timer_command_udp("remove_timer", {"task_id": int(task_id)})
            elif operation == "query":
                result = ctl.send_timer_command_udp("query_timer", {"task_id": int(task_id)})
            elif operation == "list":
                result = ctl.send_timer_command_udp("list_timer")
            elif operation == "stats":
                result = ctl.send_timer_command_udp("stats_timer")
            else:
                result = ctl.send_timer_command_udp("clear_timer")

            st.json(result)
        except Exception as exc:
            st.error(str(exc))
        finally:
            pass


def show_ambl_tab(cfg: ControllerConfig) -> None:
    st.subheader("AMBL 实时流")
    sequence = st.number_input("sequence", min_value=0, max_value=2**31 - 1, value=1, step=1)
    channels = st.number_input("channels", min_value=1, max_value=500, value=4, step=1)
    r = st.slider("R", min_value=0, max_value=255, value=255)
    g = st.slider("G", min_value=0, max_value=255, value=0)
    b = st.slider("B", min_value=0, max_value=255, value=0)
    a = st.slider("A", min_value=0, max_value=255, value=255)

    if st.button("发送 AMBL"):
        ctl = AputureController(cfg)
        rgba = [(r, g, b, a) for _ in range(int(channels))]
        try:
            ctl.send_ambl_frame(sequence=int(sequence), rgba=rgba)
            st.success("发送成功")
        except Exception as exc:
            st.error(str(exc))


def show_ble_tab() -> None:
    st.subheader("BLE 倒计时编码")
    timer_type = st.selectbox("type", options=["once", "daily", "weekly"], index=0, key="ble_type")
    trigger_time = st.text_input("trigger_time", value="2026-04-21T20:10:05", key="ble_trigger_time")
    weekday = st.number_input("weekday(weekly用)", min_value=0, max_value=6, value=2, step=1, key="ble_weekday")

    state = build_state("BLE_")
    if st.button("生成 TLV/CRC"):
        try:
            tlv = AputureController.build_ble_timer_tlv(
                timer_type=timer_type,
                trigger_time=trigger_time,
                state_fields=state,
                weekday=(int(weekday) if timer_type == "weekly" else None),
            )
            crc = AputureController.ble_crc16_a001(tlv)
            st.code(tlv.hex())
            st.write(f"CRC16: {hex(crc)}")
        except Exception as exc:
            st.error(str(exc))


def show_batch_tab(cfg: ControllerConfig, fixed_transport: Optional[str] = None, key_prefix: str = "batch") -> None:
    st.subheader("SDK 批量创建")
    transport = "udp"
    st.caption("当前传输方式: UDP")

    timer_type = st.selectbox("batch type", options=["once", "daily", "weekly"], index=0, key=f"{key_prefix}_type")
    trigger_times = st.text_area(
        "trigger_times（每行一个）",
        value="2026-04-21T23:00:00\n2026-04-21T23:05:00\n2026-04-21T23:10:00",
        height=100,
        key=f"{key_prefix}_trigger_times",
    )
    retries = st.number_input("retries", min_value=0, max_value=10, value=2, step=1, key=f"{key_prefix}_retries")
    retry_delay = st.number_input("retry_delay", min_value=0.0, max_value=10.0, value=0.3, step=0.1, key=f"{key_prefix}_retry_delay")
    rollback = st.checkbox("失败回滚", value=True, key=f"{key_prefix}_rollback")

    state = build_state(f"{key_prefix}_批量_")

    if st.button("执行批量创建", key=f"{key_prefix}_run"):
        sdk = AputureSDK(cfg)
        lines = [x.strip() for x in trigger_times.splitlines() if x.strip()]
        items = [(timer_type, t, LightState(**state)) for t in lines]
        if not items:
            st.error("请至少输入一个 trigger_time")
            return

        try:
            sdk.connect()
            result = sdk.batch_create_timers(
                items=items,
                transport=transport,
                retries=int(retries),
                retry_delay=float(retry_delay),
                rollback_on_error=rollback,
            )
            st.json(result)
        except DeviceCommandError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(str(exc))
        finally:
            sdk.disconnect()


def show_scan_tab(cfg: ControllerConfig) -> None:
    st.subheader("主动扫描（UDP 5569）")
    cidr = st.text_input("扫描网段 CIDR", value=_default_cidr_from_ip(cfg.device_ip))
    cmd = st.selectbox("探测命令", options=["stats_timer", "list_timer", "query_timer", "clear_timer"], index=0)
    timeout = st.number_input("超时(秒)", min_value=0.05, max_value=3.0, value=0.35, step=0.05)
    workers = st.number_input("并发线程", min_value=1, max_value=256, value=64, step=1)
    max_hosts = st.number_input("最大主机数", min_value=1, max_value=4096, value=512, step=1)
    include_error = st.checkbox("包含超时/错误项", value=False)
    filepath = st.text_input("保存路径", value="devices.json")

    col1, col2 = st.columns(2)
    with col1:
        scan_btn = st.button("开始扫描")
    with col2:
        save_btn = st.button("扫描并保存")

    if scan_btn or save_btn:
        try:
            items = AputureController.active_scan_udp_timer(
                cidr=cidr,
                timeout=float(timeout),
                max_workers=int(workers),
                max_hosts=int(max_hosts),
                cmd=cmd,
                include_error=include_error,
            )
            st.success(f"扫描完成，返回 {len(items)} 条结果")
            st.json(items)

            if save_btn:
                try:
                    mgr = DeviceListManager(filepath)
                    mgr.save(items)
                    st.info(f"已保存到: {filepath}")
                except Exception as exc:
                    st.error(f"保存失败: {exc}")
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("设备列表管理")
    mgr_path = st.text_input("加载设备列表路径", value="devices.json", key="mgr_path")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("加载列表"):
            try:
                mgr = DeviceListManager(mgr_path)
                devices = mgr.load()
                st.success(f"已加载 {len(devices)} 个设备")
                st.json(devices)
            except Exception as exc:
                st.error(str(exc))

    with col2:
        if st.button("查看 IP 列表"):
            try:
                mgr = DeviceListManager(mgr_path)
                ips = mgr.list_ips()
                st.write(f"共 {len(ips)} 个 IP:")
                st.code("\n".join(ips))
            except Exception as exc:
                st.error(str(exc))

    with col3:
        if st.button("清空列表"):
            try:
                mgr = DeviceListManager(mgr_path)
                mgr.clear()
                st.success("已清空")
            except Exception as exc:
                st.error(str(exc))


def show_batch_device_tab() -> None:
    st.subheader("设备快速控制")
    device_list_path = st.text_input("设备列表文件", value="devices.json", key="batch_device_path")

    try:
        batch_ctl = BatchDeviceController.from_file(device_list_path)
        ips = batch_ctl.get_ips()
    except Exception as exc:
        st.error(f"加载设备列表失败: {exc}")
        return

    if not ips:
        st.warning("设备列表为空")
        return

    st.write(f"**已加载 {len(ips)} 个设备**")

    operation = st.radio("操作类型", options=["批量灯光", "批量倒计时"], horizontal=True, key="batch_device_operation")

    col1, col2 = st.columns(2)
    with col1:
        st.write("**设备选择**")
        select_all = st.checkbox("全选", value=True, key="batch_device_select_all")
        if select_all:
            selected_ips = ips
        else:
            selected_ips = st.multiselect("选择 IP", options=ips, default=[] if not ips else [ips[0]], key="batch_device_selected_ips")
    
    if not selected_ips:
        st.warning("请至少选择一个设备")
        return

    with col2:
        st.write(f"**已选择 {len(selected_ips)} 个设备**")
        st.code("\n".join(selected_ips))

    st.divider()

    if operation == "批量灯光":
        st.subheader("MQTT 灯光参数")
        state = build_state("批量灯光_")
        mqtt_host = st.text_input("MQTT Host", value="broker.emqx.io", key="batch_device_mqtt_host")
        mqtt_port = st.number_input("MQTT Port", min_value=1, max_value=65535, value=8883, step=1, key="batch_device_mqtt_port")
        mqtt_tls = st.checkbox("MQTT TLS", value=True, key="batch_device_mqtt_tls")

        if st.button("执行批量灯光"):
            try:
                result = batch_ctl.batch_light_control(
                    ips=selected_ips,
                    state=state,
                    mqtt_host=mqtt_host,
                    mqtt_port=int(mqtt_port),
                    mqtt_tls=mqtt_tls,
                    skip_errors=True,
                )
                st.json(result)
            except Exception as exc:
                st.error(str(exc))

    else:
        st.subheader("UDP 倒计时参数")
        cmd = st.selectbox("命令", options=["stats_timer", "list_timer", "query_timer", "clear_timer"], index=0, key="batch_device_timer_cmd")
        timeout = st.number_input("超时(秒)", min_value=0.1, max_value=5.0, value=1.5, step=0.1, key="batch_device_timer_timeout")

        task_id = None
        if cmd in {"remove_timer", "query_timer"}:
            task_id = st.number_input("task_id", min_value=0, value=101, step=1)

        if st.button("执行批量倒计时"):
            payload = {}
            if task_id is not None:
                payload["task_id"] = int(task_id)

            try:
                result = batch_ctl.batch_timer_command(
                    ips=selected_ips,
                    cmd=cmd,
                    payload=payload if payload else None,
                    timeout=float(timeout),
                    skip_errors=True,
                )
                st.json(result)
            except Exception as exc:
                st.error(str(exc))


def main() -> None:
    st.set_page_config(page_title="Aputure Controller UI", layout="wide")
    st.title("Aputure IP 控制器 UI")

    cfg = build_config()
    show_mqtt_status_panel(cfg)

    tab_mqtt, tab_udp, tab_ble, tab_manage = st.tabs([
        "MQTT",
        "UDP",
        "BLE",
        "设备管理",
    ])

    with tab_mqtt:
        show_mqtt_dialog_tab(cfg)

    with tab_udp:
        show_timer_tab(cfg, fixed_transport="udp", key_prefix="udp_timer")
        st.divider()
        show_ambl_tab(cfg)
        st.divider()
        show_scan_tab(cfg)

    with tab_ble:
        show_ble_tab()

    with tab_manage:
        show_batch_device_tab()


if __name__ == "__main__":
    main()
