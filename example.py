from controller import ControllerConfig
from sdk import AputureSDK, DeviceCommandError, LightState


def main() -> None:
    cfg = ControllerConfig(
        mac="11:22:33:aa:bb:cc",
        device_ip="192.168.1.100",
    )

    sdk = AputureSDK(cfg)

    try:
        resp = sdk.create_timer(
            timer_type="once",
            trigger_time="2026-04-21T23:00:00",
            state=LightState(power=True, mode="cct", lightness=75, cct=4500),
            transport="udp",
        )
        print("create_timer:", resp)

        print("list_timers:", sdk.list_timers("udp"))
        print("stats_timers:", sdk.stats_timers("udp"))
    except DeviceCommandError as exc:
        print("设备返回失败:", exc)


if __name__ == "__main__":
    main()
