from controller import ControllerConfig
from sdk import AputureSDK, DeviceCommandError, LightState


def main() -> None:
    cfg = ControllerConfig(
        mac="11:22:33:aa:bb:cc",
        device_ip="192.168.1.100",
    )

    sdk = AputureSDK(cfg)
    sdk.connect()

    try:
        batch = [
            ("once", "2026-04-21T23:00:00", LightState(power=True, mode="cct", lightness=40, cct=3200)),
            ("once", "2026-04-21T23:05:00", LightState(power=True, mode="cct", lightness=60, cct=4300)),
            ("once", "2026-04-21T23:10:00", LightState(power=True, mode="hsi", hue=120, sat=80, lightness=70)),
        ]

        create_resp = sdk.batch_create_timers(
            items=batch,
            transport="mqtt",
            retries=2,
            retry_delay=0.3,
            rollback_on_error=True,
        )
        print("batch_create:", create_resp)

        remove_resp = sdk.batch_remove_timers(create_resp["task_ids"], transport="mqtt", retries=2)
        print("batch_remove:", remove_resp)

    except DeviceCommandError as exc:
        print("批量任务失败:", exc)
    finally:
        sdk.disconnect()


if __name__ == "__main__":
    main()
