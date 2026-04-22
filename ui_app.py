from __future__ import annotations

from typing import Any, Dict, Optional

try:
    import streamlit as st  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover
    raise SystemExit("请先安装依赖: pip install -r requirements.txt") from exc

from controller import AputureController, ControllerConfig
from sdk import AputureSDK, DeviceCommandError, LightState
from device_manager import DeviceListManager
from batch_controller import BatchDeviceController


def _default_cidr_from_ip(ip: str) -> str:
    parts = ip.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return "192.168.1.0/24"


def build_config() -> ControllerConfig:
    st.sidebar.header("设备配置")
    mac = st.sidebar.text_input("MAC", value="11:22:33:aa:bb:cc")
    device_ip = st.sidebar.text_input("设备 IP", value="192.168.1.100")
    mqtt_host = st.sidebar.text_input("MQTT Host", value="broker.emqx.io")
    mqtt_port = st.sidebar.number_input("MQTT Port", min_value=1, max_value=65535, value=8883, step=1)
    mqtt_username = st.sidebar.text_input("MQTT 用户名", value="")
    mqtt_password = st.sidebar.text_input("MQTT 密码", value="", type="password")
    mqtt_tls = st.sidebar.checkbox("MQTT TLS", value=True)

    return ControllerConfig(
        mac=mac,
        device_ip=device_ip,
        mqtt_host=mqtt_host,
        mqtt_port=int(mqtt_port),
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        mqtt_tls=mqtt_tls,
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
    with st.form("light_form"):
        state = build_state("灯光_")
        submitted = st.form_submit_button("发送")

    if submitted:
        ctl = AputureController(cfg)
        try:
            ctl.connect_mqtt()
            ctl.send_light_control(state)
            st.success("发送成功")
        except Exception as exc:
            st.error(str(exc))
        finally:
            ctl.disconnect_mqtt()


def show_timer_tab(cfg: ControllerConfig) -> None:
    st.subheader("倒计时命令")
    transport = st.radio("传输", options=["mqtt", "udp"], horizontal=True)
    operation = st.selectbox("命令", options=["add", "remove", "query", "list", "stats", "clear"])

    task_id = st.number_input("task_id", min_value=0, max_value=2**31 - 1, value=101, step=1)
    timer_type = st.selectbox("type", options=["once", "daily", "weekly"], index=0)
    trigger_time = st.text_input("trigger_time", value="2026-04-21T23:00:00")

    state = build_state("定时_") if operation == "add" else {}

    if st.button("执行", key="timer_run"):
        ctl = AputureController(cfg)
        try:
            if transport == "mqtt":
                ctl.connect_mqtt()

            if operation == "add":
                if transport == "mqtt":
                    result = ctl.add_timer_mqtt(int(task_id), timer_type, trigger_time, **state)
                else:
                    payload = {"task_id": int(task_id), "type": timer_type, "trigger_time": trigger_time, **state}
                    result = ctl.send_timer_command_udp("add_timer", payload=payload)
            elif operation == "remove":
                result = ctl.remove_timer_mqtt(int(task_id)) if transport == "mqtt" else ctl.send_timer_command_udp("remove_timer", {"task_id": int(task_id)})
            elif operation == "query":
                result = ctl.query_timer_mqtt(int(task_id)) if transport == "mqtt" else ctl.send_timer_command_udp("query_timer", {"task_id": int(task_id)})
            elif operation == "list":
                result = ctl.list_timer_mqtt() if transport == "mqtt" else ctl.send_timer_command_udp("list_timer")
            elif operation == "stats":
                result = ctl.stats_timer_mqtt() if transport == "mqtt" else ctl.send_timer_command_udp("stats_timer")
            else:
                result = ctl.clear_timer_mqtt() if transport == "mqtt" else ctl.send_timer_command_udp("clear_timer")

            st.json(result)
        except Exception as exc:
            st.error(str(exc))
        finally:
            ctl.disconnect_mqtt()


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
    timer_type = st.selectbox("type", options=["once", "daily", "weekly"], index=0)
    trigger_time = st.text_input("trigger_time", value="2026-04-21T20:10:05")
    weekday = st.number_input("weekday(weekly用)", min_value=0, max_value=6, value=2, step=1)

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


def show_batch_tab(cfg: ControllerConfig) -> None:
    st.subheader("SDK 批量创建")
    transport = st.radio("batch transport", options=["mqtt", "udp"], horizontal=True)
    timer_type = st.selectbox("batch type", options=["once", "daily", "weekly"], index=0)
    trigger_times = st.text_area(
        "trigger_times（每行一个）",
        value="2026-04-21T23:00:00\n2026-04-21T23:05:00\n2026-04-21T23:10:00",
        height=100,
    )
    retries = st.number_input("retries", min_value=0, max_value=10, value=2, step=1)
    retry_delay = st.number_input("retry_delay", min_value=0.0, max_value=10.0, value=0.3, step=0.1)
    rollback = st.checkbox("失败回滚", value=True)

    state = build_state("批量_")

    if st.button("执行批量创建"):
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

    operation = st.radio("操作类型", options=["批量灯光", "批量倒计时"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        st.write("**设备选择**")
        select_all = st.checkbox("全选", value=True)
        if select_all:
            selected_ips = ips
        else:
            selected_ips = st.multiselect("选择 IP", options=ips, default=[] if not ips else [ips[0]])
    
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
        mqtt_host = st.text_input("MQTT Host", value="broker.emqx.io")
        mqtt_port = st.number_input("MQTT Port", min_value=1, max_value=65535, value=8883, step=1)
        mqtt_tls = st.checkbox("MQTT TLS", value=True)

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
        cmd = st.selectbox("命令", options=["stats_timer", "list_timer", "query_timer", "clear_timer"], index=0)
        timeout = st.number_input("超时(秒)", min_value=0.1, max_value=5.0, value=1.5, step=0.1)

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

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "灯光控制",
        "倒计时",
        "AMBL",
        "BLE 编码",
        "批量任务",
        "主动扫描",
        "设备快速控制",
    ])

    with tab1:
        show_light_tab(cfg)
    with tab2:
        show_timer_tab(cfg)
    with tab3:
        show_ambl_tab(cfg)
    with tab4:
        show_ble_tab()
    with tab5:
        show_batch_tab(cfg)
    with tab6:
        show_scan_tab(cfg)
    with tab7:
        show_batch_device_tab()


if __name__ == "__main__":
    main()
