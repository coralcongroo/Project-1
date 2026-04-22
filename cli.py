from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional

from controller import AputureController, ControllerConfig
from sdk import AputureSDK, LightState
from device_manager import DeviceListManager


def _build_config(args: argparse.Namespace) -> ControllerConfig:
    return ControllerConfig(
        mac=args.mac,
        device_ip=args.device_ip,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        mqtt_tls=(not args.no_tls),
    )


def _state_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    state: Dict[str, Any] = {}
    for key in ["power", "mode", "level", "lightness", "cct", "gm", "hue", "sat", "x", "y"]:
        value = getattr(args, key, None)
        if value is not None:
            state[key] = value
    return state


def _print_result(result: Dict[str, Any]) -> None:
    print(json.dumps(result, ensure_ascii=False, indent=2))


def run_light(args: argparse.Namespace) -> None:
    raise RuntimeError("已切换为 MQTT Server 模式，不再提供 MQTT 客户端 light 下发")


def run_timer(args: argparse.Namespace) -> None:
    cfg = _build_config(args)
    transport = args.transport

    if transport == "mqtt":
        raise RuntimeError("已切换为 MQTT Server 模式，不再提供 MQTT 客户端 timer 下发")

    ctl = AputureController(cfg)
    result = _run_timer_with_controller(ctl, args, transport)
    _print_result(result)


def _run_timer_with_controller(ctl: AputureController, args: argparse.Namespace, transport: str) -> Dict[str, Any]:
    op = args.operation
    if transport != "udp":
        raise RuntimeError("当前模式仅支持 UDP")

    if op == "add":
        payload = {
            "task_id": args.task_id,
            "type": args.type,
            "trigger_time": args.trigger_time,
            **_state_from_args(args),
        }
        return ctl.send_timer_command_udp("add_timer", payload)

    if op == "remove":
        return ctl.send_timer_command_udp("remove_timer", {"task_id": args.task_id})

    if op == "query":
        return ctl.send_timer_command_udp("query_timer", {"task_id": args.task_id})

    if op == "list":
        return ctl.send_timer_command_udp("list_timer")

    if op == "stats":
        return ctl.send_timer_command_udp("stats_timer")

    if op == "clear":
        return ctl.send_timer_command_udp("clear_timer")

    raise ValueError(f"unsupported timer operation: {op}")


def run_ambl(args: argparse.Namespace) -> None:
    cfg = _build_config(args)
    ctl = AputureController(cfg)

    rgba = [
        (args.r, args.g, args.b, args.a)
        for _ in range(args.channels)
    ]
    ctl.send_ambl_frame(sequence=args.sequence, rgba=rgba)
    print("ok")


def run_ble_encode(args: argparse.Namespace) -> None:
    state = _state_from_args(args)
    tlv = AputureController.build_ble_timer_tlv(
        timer_type=args.type,
        trigger_time=args.trigger_time,
        state_fields=state,
        weekday=args.weekday,
    )
    crc = AputureController.ble_crc16_a001(tlv)
    print("tlv_hex:", tlv.hex())
    print("crc16:", hex(crc))


def run_sdk_batch(args: argparse.Namespace) -> None:
    cfg = _build_config(args)
    sdk = AputureSDK(cfg)

    items: List[tuple[str, str, LightState]] = []
    for trigger in args.trigger_times:
        items.append(
            (
                args.type,
                trigger,
                LightState(**_state_from_args(args)),
            )
        )

    if args.transport == "mqtt":
        raise RuntimeError("已切换为 MQTT Server 模式，不再提供 MQTT 客户端 batch-add")

    result = sdk.batch_create_timers(
        items=items,
        transport=args.transport,
        retries=args.retries,
        retry_delay=args.retry_delay,
        rollback_on_error=(not args.no_rollback),
    )
    _print_result(result)


def run_scan(args: argparse.Namespace) -> None:
    result = AputureController.active_scan_udp_timer(
        cidr=args.cidr,
        timeout=args.timeout,
        max_workers=args.workers,
        max_hosts=args.max_hosts,
        cmd=args.cmd,
        include_error=args.include_error,
    )
    print_data = {"result": "ok", "count": len(result), "items": result}
    _print_result(print_data)

    if args.save:
        try:
            mgr = DeviceListManager(args.save)
            mgr.save(result)
            print(f"已保存到: {args.save}", flush=True)
        except Exception as exc:
            print(f"保存失败: {exc}", flush=True)


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mac", required=True, help="设备 MAC，例如 11:22:33:aa:bb:cc")
    parser.add_argument("--device-ip", required=True, help="设备 IPv4")
    parser.add_argument("--mqtt-host", default="broker.emqx.io")
    parser.add_argument("--mqtt-port", type=int, default=8883)
    parser.add_argument("--mqtt-username", default="")
    parser.add_argument("--mqtt-password", default="")
    parser.add_argument("--no-tls", action="store_true", help="关闭 MQTT TLS")


def add_state_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--power", type=lambda x: x.lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--mode", choices=["cct", "hsi", "xy"])
    parser.add_argument("--level", type=int)
    parser.add_argument("--lightness", type=float)
    parser.add_argument("--cct", type=int)
    parser.add_argument("--gm", type=float)
    parser.add_argument("--hue", type=float)
    parser.add_argument("--sat", type=float)
    parser.add_argument("--x", type=float)
    parser.add_argument("--y", type=float)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aputure IP Controller CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_timer = sub.add_parser("timer", help="倒计时命令")
    add_common(p_timer)
    p_timer.add_argument("--transport", choices=["udp"], default="udp")
    p_timer.add_argument("operation", choices=["add", "remove", "query", "list", "stats", "clear"])
    p_timer.add_argument("--task-id", type=int)
    p_timer.add_argument("--type", choices=["once", "daily", "weekly"], default="once")
    p_timer.add_argument("--trigger-time")
    add_state_options(p_timer)
    p_timer.set_defaults(func=run_timer)

    p_ambl = sub.add_parser("ambl", help="发送 AMBL 实时帧")
    add_common(p_ambl)
    p_ambl.add_argument("--sequence", type=int, required=True)
    p_ambl.add_argument("--channels", type=int, default=1)
    p_ambl.add_argument("--r", type=int, default=255)
    p_ambl.add_argument("--g", type=int, default=255)
    p_ambl.add_argument("--b", type=int, default=255)
    p_ambl.add_argument("--a", type=int, default=255)
    p_ambl.set_defaults(func=run_ambl)

    p_ble = sub.add_parser("ble-encode", help="生成 BLE 倒计时 TLV/CRC")
    p_ble.add_argument("--type", choices=["once", "daily", "weekly"], required=True)
    p_ble.add_argument("--trigger-time", required=True)
    p_ble.add_argument("--weekday", type=int)
    add_state_options(p_ble)
    p_ble.set_defaults(func=run_ble_encode)

    p_batch = sub.add_parser("batch-add", help="SDK 批量创建倒计时")
    add_common(p_batch)
    p_batch.add_argument("--transport", choices=["udp"], default="udp")
    p_batch.add_argument("--type", choices=["once", "daily", "weekly"], default="once")
    p_batch.add_argument("--trigger-times", nargs="+", required=True)
    p_batch.add_argument("--retries", type=int, default=2)
    p_batch.add_argument("--retry-delay", type=float, default=0.3)
    p_batch.add_argument("--no-rollback", action="store_true")
    add_state_options(p_batch)
    p_batch.set_defaults(func=run_sdk_batch)

    p_scan = sub.add_parser("scan", help="主动扫描 UDP5569 设备")
    p_scan.add_argument("--cidr", required=True, help="IPv4 网段，例如 192.168.1.0/24")
    p_scan.add_argument("--cmd", choices=["stats_timer", "list_timer", "query_timer", "clear_timer"], default="stats_timer")
    p_scan.add_argument("--timeout", type=float, default=0.35)
    p_scan.add_argument("--workers", type=int, default=64)
    p_scan.add_argument("--max-hosts", type=int, default=512)
    p_scan.add_argument("--include-error", action="store_true")
    p_scan.add_argument("--save", type=str, help="保存扫描结果到文件")
    p_scan.set_defaults(func=run_scan)

    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.command == "timer":
        if args.operation in {"remove", "query"} and args.task_id is None:
            raise ValueError("timer remove/query 需要 --task-id")
        if args.operation == "add":
            if args.task_id is None:
                raise ValueError("timer add 需要 --task-id")
            if not args.trigger_time:
                raise ValueError("timer add 需要 --trigger-time")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        validate_args(args)
        args.func(args)
    except Exception as exc:
        print(f"error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
