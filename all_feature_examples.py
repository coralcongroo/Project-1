from __future__ import annotations

from controller import AputureController, ControllerConfig
from sdk import AputureSDK, DeviceCommandError, LightState


CFG = ControllerConfig(
    mac="11:22:33:aa:bb:cc",
    device_ip="192.168.1.100",
)


def example_mqtt_light_control() -> None:
    """MQTT 灯光控制：上电 + CCT 模式。"""
    ctl = AputureController(CFG)
    ctl.connect_mqtt()
    try:
        ctl.send_light_control({"power": True, "mode": "cct", "lightness": 70, "cct": 4500})
        ctl.send_light_control({"mode": "hsi", "hue": 200, "sat": 80, "lightness": 60})
        ctl.send_light_control({"mode": "xy", "x": 0.31, "y": 0.33, "lightness": 55})
    finally:
        ctl.disconnect_mqtt()


def example_mqtt_timer_commands() -> None:
    """MQTT 倒计时：add/query/list/stats/remove/clear。"""
    ctl = AputureController(CFG)
    ctl.connect_mqtt()
    try:
        print("add:", ctl.add_timer_mqtt(101, "once", "2026-04-21T23:00:00", power=True, mode="cct", lightness=75, cct=4300))
        print("query:", ctl.query_timer_mqtt(101))
        print("list:", ctl.list_timer_mqtt())
        print("stats:", ctl.stats_timer_mqtt())
        print("remove:", ctl.remove_timer_mqtt(101))
        print("clear:", ctl.clear_timer_mqtt())
    finally:
        ctl.disconnect_mqtt()


def example_udp_timer_commands() -> None:
    """UDP 5569 倒计时命令。"""
    ctl = AputureController(CFG)

    print(
        "udp_add:",
        ctl.send_timer_command_udp(
            "add_timer",
            payload={
                "task_id": 201,
                "type": "once",
                "trigger_time": "2026-04-21 23:30:00",
                "power": True,
                "mode": "cct",
                "lightness": 65,
                "cct": 5000,
            },
        ),
    )
    print("udp_query:", ctl.send_timer_command_udp("query_timer", payload={"task_id": 201}))
    print("udp_list:", ctl.send_timer_command_udp("list_timer"))
    print("udp_stats:", ctl.send_timer_command_udp("stats_timer"))
    print("udp_remove:", ctl.send_timer_command_udp("remove_timer", payload={"task_id": 201}))


def example_ambl_realtime_stream() -> None:
    """UDP 5568 AMBL 实时流（4 通道 RGBA）。"""
    ctl = AputureController(CFG)
    rgba_channels = [
        (255, 0, 0, 255),
        (0, 255, 0, 255),
        (0, 0, 255, 255),
        (255, 255, 255, 255),
    ]
    ctl.send_ambl_frame(sequence=1, rgba=rgba_channels)


def example_ble_tlv_and_crc() -> None:
    """BLE 倒计时 TLV + CRC16(0xA001)。"""
    tlv = AputureController.build_ble_timer_tlv(
        timer_type="weekly",
        trigger_time="2026-04-21T20:10:05",
        weekday=2,
        state_fields={
            "power": True,
            "mode": "cct",
            "lightness": 50,
            "cct": 4200,
        },
    )
    crc = AputureController.ble_crc16_a001(tlv)
    print("ble_tlv_hex:", tlv.hex())
    print("ble_crc16:", hex(crc))


def example_sdk_basic() -> None:
    """SDK 基础流程：连接、控灯、建任务、查询、断开。"""
    sdk = AputureSDK(CFG)
    sdk.connect()
    try:
        sdk.set_light(LightState(power=True, mode="cct", lightness=68, cct=4300))

        create_resp = sdk.create_timer(
            timer_type="once",
            trigger_time="2026-04-21T23:00:00",
            state=LightState(power=True, mode="cct", lightness=75, cct=4500),
            transport="mqtt",
        )
        print("sdk_create:", create_resp)
        print("sdk_list:", sdk.list_timers("mqtt"))
        print("sdk_stats:", sdk.stats_timers("mqtt"))
    except DeviceCommandError as exc:
        print("sdk_error:", exc)
    finally:
        sdk.disconnect()


def example_sdk_batch() -> None:
    """SDK 批量：失败重试 + 可选回滚。"""
    sdk = AputureSDK(CFG)
    sdk.connect()
    try:
        batch_items = [
            ("once", "2026-04-21T23:00:00", LightState(power=True, mode="cct", lightness=40, cct=3200)),
            ("once", "2026-04-21T23:05:00", LightState(power=True, mode="cct", lightness=60, cct=4300)),
            ("once", "2026-04-21T23:10:00", LightState(power=True, mode="hsi", hue=120, sat=80, lightness=70)),
        ]

        result = sdk.batch_create_timers(
            items=batch_items,
            transport="mqtt",
            retries=2,
            retry_delay=0.3,
            rollback_on_error=True,
        )
        print("batch_create:", result)

        task_ids = result.get("task_ids", [])
        if task_ids:
            print("batch_remove:", sdk.batch_remove_timers(task_ids, transport="mqtt", retries=2))
    except DeviceCommandError as exc:
        print("batch_error:", exc)
    finally:
        sdk.disconnect()


def example_active_scan() -> None:
    """主动扫描网段 UDP5569 响应设备。"""
    items = AputureController.active_scan_udp_timer(
        cidr="192.168.1.0/24",
        timeout=0.35,
        max_workers=64,
        max_hosts=512,
        cmd="stats_timer",
        include_error=False,
    )
    print("scan_count:", len(items))
    print("scan_items:", items)


if __name__ == "__main__":
    # 按需取消注释运行
    # example_mqtt_light_control()
    # example_mqtt_timer_commands()
    # example_udp_timer_commands()
    # example_ambl_realtime_stream()
    # example_ble_tlv_and_crc()
    # example_sdk_basic()
    # example_sdk_batch()
    # example_active_scan()
    pass
