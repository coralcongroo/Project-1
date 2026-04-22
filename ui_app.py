from __future__ import annotations

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
    st.subheader("MQTT 对话框（Server 管理）")
    mgr = _get_server_manager()

    st.markdown("**服务器日志显示框**")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        refresh = st.button("刷新日志", key="mqtt_server_refresh")
    with c2:
        if st.button("清空日志", key="mqtt_server_clear_log"):
            mgr.log_path.write_text("", encoding="utf-8")
            st.info("已清空日志")
    with c3:
        max_lines = st.number_input("显示行数", min_value=20, max_value=1000, value=200, step=20, key="mqtt_server_log_lines")

    if refresh or True:
        logs = mgr.tail_logs(max_lines=int(max_lines))
        st.text_area("Server Logs", value=logs or "(暂无日志)", height=260, key="mqtt_server_log_text")

    st.markdown("**Server 控制框**")
    listener_host = st.text_input("监听地址", value=cfg.mqtt_host, key="mqtt_server_host")
    listener_port = st.number_input("监听端口", min_value=1, max_value=65535, value=int(cfg.mqtt_port), step=1, key="mqtt_server_port")
    allow_anonymous = st.checkbox("允许匿名连接", value=False, key="mqtt_server_allow_anon")
    password_file = st.text_input("密码文件（可选）", value="", key="mqtt_server_password_file")
    acl_file = st.text_input("ACL 文件（可选）", value=str(mgr.workspace / "mosquitto.acl"), key="mqtt_server_acl_file")

    st.markdown("**TLS 配置（建议按 server.md 使用 8883 + TLSv1.2）**")
    tls_enabled = st.checkbox("启用 TLS", value=True, key="mqtt_server_tls_enabled")
    cafile = st.text_input("CA 文件", value="/etc/emqx/certs/ca.crt", key="mqtt_server_cafile")
    certfile = st.text_input("服务端证书", value="/etc/emqx/certs/server.crt", key="mqtt_server_certfile")
    keyfile = st.text_input("服务端私钥", value="/etc/emqx/certs/server.key", key="mqtt_server_keyfile")

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

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        if st.button("启动 Server", key="mqtt_server_start"):
            ok, msg = mgr.start(
                MqttServerConfig(
                    listener_host=listener_host,
                    listener_port=int(listener_port),
                    allow_anonymous=allow_anonymous,
                    password_file=password_file,
                    acl_file=acl_file,
                    tls_enabled=tls_enabled,
                    cafile=cafile,
                    certfile=certfile,
                    keyfile=keyfile,
                )
            )
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    with s2:
        if st.button("停止 Server", key="mqtt_server_stop"):
            ok, msg = mgr.stop()
            if ok:
                st.info(msg)
            else:
                st.error(msg)
    with s3:
        if st.button("重启 Server", key="mqtt_server_restart"):
            mgr.stop()
            ok, msg = mgr.start(
                MqttServerConfig(
                    listener_host=listener_host,
                    listener_port=int(listener_port),
                    allow_anonymous=allow_anonymous,
                    password_file=password_file,
                    acl_file=acl_file,
                    tls_enabled=tls_enabled,
                    cafile=cafile,
                    certfile=certfile,
                    keyfile=keyfile,
                )
            )
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    with s4:
        if st.button("检测监听", key="mqtt_server_probe"):
            ok, msg = mgr.check_listener(listener_host, int(listener_port))
            if ok:
                st.success(msg)
            else:
                st.warning(msg)

    st.caption(f"当前状态: {mgr.status_text()}")

    st.markdown("**预设 Server 参数**")
    p1, p2, p3 = st.columns(3)
    with p1:
        if st.button("预设：本机调试 127.0.0.1:1883", key="mqtt_server_preset_local"):
            st.session_state.mqtt_server_host = "127.0.0.1"
            st.session_state.mqtt_server_port = 1883
            st.rerun()
    with p2:
        if st.button("预设：局域网 0.0.0.0:1883", key="mqtt_server_preset_lan"):
            st.session_state.mqtt_server_host = "0.0.0.0"
            st.session_state.mqtt_server_port = 1883
            st.rerun()
    with p3:
        if st.button("预设：MQTTS 0.0.0.0:8883", key="mqtt_server_preset_mqtts"):
            st.session_state.mqtt_server_host = "0.0.0.0"
            st.session_state.mqtt_server_port = 8883
            st.rerun()


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
