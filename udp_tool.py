#!/usr/bin/env python3
"""UDP test tool for Aputure IP Project.

Examples:
  python3 tools/udp_tool/udp_tool.py ambl --pixels 255,0,0,255
  python3 tools/udp_tool/udp_tool.py ambl --pixels "255,0,0,255;0,255,0,255;0,0,255,255"
    python3 tools/udp_tool/udp_tool.py ambl --pixels 255,0,0,255 --count 100 --interval-ms 33
    python3 tools/udp_tool/udp_tool.py ambl --pixels "255,0,0,255;0,255,0,255" --repeat --interval-ms 16
  python3 tools/udp_tool/udp_tool.py json --target 192.168.9.100 --payload '{"cmd":"list_timer"}'
  python3 tools/udp_tool/udp_tool.py json --target 192.168.9.100 --payload-file payload.json
  python3 tools/udp_tool/udp_tool.py listen --port 5569
"""

from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
import time
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


AMBL_MAGIC = 0x414D424C
AMBL_VERSION = 1
AMBL_HEADER_SIZE = 24
DEFAULT_AMBL_TARGET = "239.255.23.42"
DEFAULT_AMBL_PORT = 5568
DEFAULT_JSON_PORT = 5569


def parse_pixel_group(text: str) -> Tuple[int, int, int, int]:
    parts = [item.strip() for item in text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"pixel must have 4 components RGBA, got: {text}")

    values = []
    for part in parts:
        try:
            value = int(part, 0)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"invalid channel value '{part}' in pixel '{text}'") from exc
        if value < 0 or value > 255:
            raise argparse.ArgumentTypeError(f"channel value out of range 0..255 in pixel '{text}'")
        values.append(value)

    return values[0], values[1], values[2], values[3]


def parse_pixels(text: str) -> List[Tuple[int, int, int, int]]:
    groups = [item.strip() for item in text.split(";") if item.strip()]
    if not groups:
        raise argparse.ArgumentTypeError("pixels cannot be empty")
    return [parse_pixel_group(group) for group in groups]


def build_ambl_packet(sequence: int, pixels: Sequence[Tuple[int, int, int, int]], timestamp_us: int | None = None) -> bytes:
    payload = bytearray()
    for red, green, blue, alpha in pixels:
        payload.extend((red, green, blue, alpha))

    if timestamp_us is None:
        timestamp_us = time.time_ns() // 1000

    return struct.pack(
        "!IHHIHHQ",
        AMBL_MAGIC,
        AMBL_VERSION,
        AMBL_HEADER_SIZE,
        sequence,
        len(payload),
        len(pixels),
        timestamp_us,
    ) + payload


def hexdump(data: bytes, width: int = 16) -> str:
    lines = []
    for offset in range(0, len(data), width):
        chunk = data[offset : offset + width]
        hex_part = " ".join(f"{byte:02x}" for byte in chunk)
        ascii_part = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
        lines.append(f"{offset:04x}  {hex_part:<{width * 3}}  {ascii_part}")
    return "\n".join(lines)


def send_ambl(args: argparse.Namespace) -> int:
    pixels = parse_pixels(args.pixels)
    send_forever = args.repeat or args.count == 0
    interval_s = args.interval_ms / 1000.0

    if send_forever:
        print(f"Streaming AMBL frames to {args.target}:{args.port}")
    else:
        print(f"Sending {args.count} AMBL frame(s) to {args.target}:{args.port}")
    print(
        f"sequence_start={args.sequence} channels={len(pixels)} interval_ms={args.interval_ms} "
        f"payload_size={len(pixels) * 4}"
    )

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, args.ttl)

        sent = 0
        sequence = args.sequence
        while send_forever or sent < args.count:
            packet = build_ambl_packet(sequence, pixels)
            if args.dump and sent == 0:
                print(hexdump(packet))

            sock.sendto(packet, (args.target, args.port))
            sent += 1
            sequence += 1

            if args.progress_every > 0 and sent % args.progress_every == 0:
                print(f"sent_frames={sent} last_sequence={sequence - 1}")

            if interval_s > 0 and (send_forever or sent < args.count):
                time.sleep(interval_s)

    print(f"Done, sent_frames={sent}")

    return 0


def load_json_payload(args: argparse.Namespace) -> str:
    if args.payload is not None and args.payload_file is not None:
        raise ValueError("use either --payload or --payload-file, not both")
    if args.payload is None and args.payload_file is None:
        raise ValueError("one of --payload or --payload-file is required")

    if args.payload_file is not None:
        return Path(args.payload_file).read_text(encoding="utf-8")
    return args.payload


def send_json(args: argparse.Namespace) -> int:
    payload_text = load_json_payload(args)
    payload_obj = json.loads(payload_text)
    payload_bytes = json.dumps(payload_obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    print(f"Sending JSON UDP to {args.target}:{args.port}")
    print(json.dumps(payload_obj, indent=2, ensure_ascii=False))

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(args.timeout)
        sock.sendto(payload_bytes, (args.target, args.port))
        if not args.expect_response:
            return 0

        try:
            response_bytes, source = sock.recvfrom(args.recv_size)
        except socket.timeout:
            print("Receive timeout")
            return 2

    print(f"Received from {source[0]}:{source[1]}")
    text = response_bytes.decode("utf-8", errors="replace")
    try:
        print(json.dumps(json.loads(text), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(text)
    return 0


def listen_udp(args: argparse.Namespace) -> int:
    print(f"Listening on {args.host}:{args.port}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((args.host, args.port))
        while True:
            data, source = sock.recvfrom(args.recv_size)
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] from {source[0]}:{source[1]} len={len(data)}")
            if args.text:
                print(data.decode("utf-8", errors="replace"))
            else:
                print(hexdump(data))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UDP test tool for Aputure IP Project")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ambl = subparsers.add_parser("ambl", help="Send one or more AMBL frames to UDP 5568")
    ambl.add_argument("--target", default=DEFAULT_AMBL_TARGET, help="Multicast target address")
    ambl.add_argument("--port", type=int, default=DEFAULT_AMBL_PORT, help="AMBL UDP port")
    ambl.add_argument("--sequence", type=int, default=1, help="AMBL frame sequence")
    ambl.add_argument(
        "--pixels",
        required=True,
        help="RGBA pixels separated by ';', e.g. '255,0,0,255;0,255,0,255'",
    )
    ambl.add_argument("--ttl", type=int, default=1, help="Multicast TTL")
    ambl.add_argument("--count", type=int, default=1, help="Number of frames to send; use 0 with --repeat for infinite loop")
    ambl.add_argument("--interval-ms", type=float, default=0.0, help="Delay between frames in milliseconds")
    ambl.add_argument("--repeat", action="store_true", help="Send continuously until interrupted")
    ambl.add_argument("--progress-every", type=int, default=100, help="Print progress every N frames; 0 disables")
    ambl.add_argument("--dump", action="store_true", help="Print packet hexdump before sending")
    ambl.set_defaults(func=send_ambl)

    json_cmd = subparsers.add_parser("json", help="Send JSON command to UDP 5569")
    json_cmd.add_argument("--target", required=True, help="Device IP address")
    json_cmd.add_argument("--port", type=int, default=DEFAULT_JSON_PORT, help="JSON command UDP port")
    json_cmd.add_argument("--payload", help="Inline JSON payload string")
    json_cmd.add_argument("--payload-file", help="Path to JSON payload file")
    json_cmd.add_argument("--timeout", type=float, default=2.0, help="Response timeout seconds")
    json_cmd.add_argument("--recv-size", type=int, default=4096, help="Receive buffer size")
    json_cmd.add_argument(
        "--no-response",
        action="store_false",
        dest="expect_response",
        help="Do not wait for UDP response",
    )
    json_cmd.set_defaults(func=send_json, expect_response=True)

    listen = subparsers.add_parser("listen", help="Listen on a UDP port and print incoming data")
    listen.add_argument("--host", default="0.0.0.0", help="Bind address")
    listen.add_argument("--port", type=int, required=True, help="UDP port to listen on")
    listen.add_argument("--recv-size", type=int, default=4096, help="Receive buffer size")
    listen.add_argument("--text", action="store_true", help="Decode payload as UTF-8 text instead of hex")
    listen.set_defaults(func=listen_udp)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(130)