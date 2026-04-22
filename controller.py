from __future__ import annotations

import json
import ipaddress
import queue
import socket
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

try:
    import paho.mqtt.client as mqtt  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    mqtt = None


MQTT_BROKER_HOST = "broker.emqx.io"
MQTT_BROKER_PORT = 8883
MQTT_REPORT_TOPIC = "report/data"
MQTT_CLIENT_PREFIX = "aputure"

UDP_TIMER_PORT = 5569
UDP_AMBL_ADDR = "239.255.23.42"
UDP_AMBL_PORT = 5568

AMBL_MAGIC = 0x414D424C
AMBL_VERSION = 1
AMBL_HEADER_SIZE = 24
AMBL_MAX_FRAME = 2048
AMBL_MAX_CHANNELS = 500


TimerType = Union[str, int]


@dataclass
class ControllerConfig:
    mac: str
    device_ip: str
    mqtt_host: str = MQTT_BROKER_HOST
    mqtt_port: int = MQTT_BROKER_PORT
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_client_prefix: str = MQTT_CLIENT_PREFIX
    mqtt_tls: bool = True
    mqtt_connect_timeout: float = 8.0
    mqtt_reconnect_min_delay: int = 1
    mqtt_reconnect_max_delay: int = 30


class ControllerError(Exception):
    pass


class ValidationError(ControllerError):
    pass


class MqttConnectionError(ControllerError):
    pass


class MqttNotConnectedError(ControllerError):
    pass


class CommandTimeoutError(ControllerError):
    pass


class CommandExecutionError(ControllerError):
    pass


class AputureController:
    def __init__(self, config: ControllerConfig) -> None:
        self.config = config
        self.mac = self._normalize_mac(config.mac)
        self._mqtt: Optional[Any] = None
        self._timer_reply_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._mqtt_lock = threading.Lock()
        self._mqtt_connected = threading.Event()
        self._last_mqtt_rc = 0

    @property
    def down_topic(self) -> str:
        return f"iot/device/{self.mac}/down"

    @property
    def timer_topic(self) -> str:
        return f"iot/device/{self.mac}/timer"

    @property
    def timer_reply_topic(self) -> str:
        return f"iot/device/{self.mac}/timer_reply"

    def connect_mqtt(self) -> None:
        if mqtt is None:
            raise MqttConnectionError("缺少 paho-mqtt，请先安装: pip install paho-mqtt")

        client_id = f"{self.config.mqtt_client_prefix}-{self.mac}"
        client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

        if self.config.mqtt_username or self.config.mqtt_password:
            client.username_pw_set(self.config.mqtt_username, self.config.mqtt_password)

        if self.config.mqtt_tls:
            client.tls_set()

        client.reconnect_delay_set(
            min_delay=self.config.mqtt_reconnect_min_delay,
            max_delay=self.config.mqtt_reconnect_max_delay,
        )

        client.on_message = self._on_mqtt_message
        client.on_connect = self._on_mqtt_connect
        client.on_disconnect = self._on_mqtt_disconnect

        self._mqtt_connected.clear()
        client.connect_async(self.config.mqtt_host, self.config.mqtt_port, keepalive=60)
        client.loop_start()
        self._mqtt = client

        if not self._mqtt_connected.wait(timeout=self.config.mqtt_connect_timeout):
            self.disconnect_mqtt()
            raise MqttConnectionError(
                f"MQTT 连接超时，host={self.config.mqtt_host}, port={self.config.mqtt_port}, rc={self._last_mqtt_rc}"
            )

    def disconnect_mqtt(self) -> None:
        if not self._mqtt:
            return
        self._mqtt.loop_stop()
        self._mqtt.disconnect()
        self._mqtt = None
        self._mqtt_connected.clear()

    def send_light_control(self, payload: Dict[str, Any], qos: int = 1) -> None:
        self._validate_light_payload(payload)
        self._publish_json(self.down_topic, payload, qos=qos)

    def send_timer_command_mqtt(
        self,
        cmd: str,
        payload: Optional[Dict[str, Any]] = None,
        wait_reply: bool = True,
        timeout: float = 5.0,
        qos: int = 1,
    ) -> Optional[Dict[str, Any]]:
        body: Dict[str, Any] = {"cmd": cmd}
        if payload:
            body.update(payload)

        self._validate_timer_payload(body)
        self._drain_timer_reply_queue()
        self._publish_json(self.timer_topic, body, qos=qos)

        if not wait_reply:
            return None

        deadline = time.time() + timeout
        while time.time() < deadline:
            remain = max(0.01, deadline - time.time())
            try:
                reply = self._timer_reply_queue.get(timeout=remain)
            except queue.Empty:
                break
            if reply.get("action") == cmd:
                return reply
        raise CommandTimeoutError(f"等待 timer_reply 超时: cmd={cmd}")

    def add_timer_mqtt(
        self,
        task_id: int,
        timer_type: TimerType,
        trigger_time: str,
        **state_fields: Any,
    ) -> Dict[str, Any]:
        payload = {
            "task_id": int(task_id),
            "type": self._normalize_timer_type(timer_type),
            "trigger_time": trigger_time,
            **state_fields,
        }
        result = self.send_timer_command_mqtt("add_timer", payload=payload, wait_reply=True)
        return result or {}

    def remove_timer_mqtt(self, task_id: int) -> Dict[str, Any]:
        result = self.send_timer_command_mqtt("remove_timer", payload={"task_id": int(task_id)}, wait_reply=True)
        return result or {}

    def clear_timer_mqtt(self) -> Dict[str, Any]:
        result = self.send_timer_command_mqtt("clear_timer", payload={}, wait_reply=True)
        return result or {}

    def query_timer_mqtt(self, task_id: int) -> Dict[str, Any]:
        result = self.send_timer_command_mqtt("query_timer", payload={"task_id": int(task_id)}, wait_reply=True)
        return result or {}

    def list_timer_mqtt(self) -> Dict[str, Any]:
        result = self.send_timer_command_mqtt("list_timer", payload={}, wait_reply=True)
        return result or {}

    def stats_timer_mqtt(self) -> Dict[str, Any]:
        result = self.send_timer_command_mqtt("stats_timer", payload={}, wait_reply=True)
        return result or {}

    def send_timer_command_udp(
        self,
        cmd: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 1.5,
        retries: int = 2,
    ) -> Dict[str, Any]:
        body = {"cmd": cmd}
        if payload:
            body.update(payload)
        self._validate_timer_payload(body)

        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        if len(data) > 1024:
            raise ValidationError("UDP 倒计时 JSON 超过 1024 字节限制")

        last_error: Optional[Exception] = None
        for _ in range(retries + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(timeout)
                    sock.sendto(data, (self.config.device_ip, UDP_TIMER_PORT))
                    resp, _ = sock.recvfrom(4096)
                return json.loads(resp.decode("utf-8"))
            except Exception as exc:
                last_error = exc
        raise CommandTimeoutError(f"UDP 命令失败: {last_error}")

    def send_ambl_frame(self, sequence: int, rgba: Union[bytes, bytearray, Iterable[Tuple[int, int, int, int]]]) -> None:
        payload = self._build_ambl_payload(rgba)
        channel_count = len(payload) // 4

        if channel_count > AMBL_MAX_CHANNELS:
            raise ValidationError(f"channel_count 超限: {channel_count}>{AMBL_MAX_CHANNELS}")

        header = struct.pack(
            "!IHHIHHQ",
            AMBL_MAGIC,
            AMBL_VERSION,
            AMBL_HEADER_SIZE,
            int(sequence) & 0xFFFFFFFF,
            len(payload),
            channel_count,
            int(time.time() * 1_000_000),
        )

        frame = header + payload
        if len(frame) > AMBL_MAX_FRAME:
            raise ValidationError(f"AMBL 帧长度超限: {len(frame)}>{AMBL_MAX_FRAME}")

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            ttl = struct.pack("b", 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
            sock.sendto(frame, (UDP_AMBL_ADDR, UDP_AMBL_PORT))

    @staticmethod
    def active_scan_udp_timer(
        cidr: str,
        timeout: float = 0.35,
        max_workers: int = 64,
        max_hosts: int = 512,
        cmd: str = "stats_timer",
        include_error: bool = False,
    ) -> List[Dict[str, Any]]:
        """主动扫描网段内响应 UDP 倒计时端口的设备。"""
        valid_cmds = {"list_timer", "stats_timer", "query_timer", "clear_timer"}
        if cmd not in valid_cmds:
            raise ValidationError(f"scan cmd 不支持: {cmd}")
        if timeout <= 0:
            raise ValidationError("timeout 必须大于 0")
        if max_workers <= 0:
            raise ValidationError("max_workers 必须大于 0")
        if max_hosts <= 0:
            raise ValidationError("max_hosts 必须大于 0")

        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError as exc:
            raise ValidationError(f"无效 CIDR: {cidr}") from exc

        if network.version != 4:
            raise ValidationError("仅支持 IPv4 网段扫描")

        hosts = [str(ip) for ip in network.hosts()]
        if len(hosts) > max_hosts:
            raise ValidationError(f"扫描主机数 {len(hosts)} 超限，max_hosts={max_hosts}")

        payload: Dict[str, Any] = {"cmd": cmd}
        if cmd == "query_timer":
            payload["task_id"] = 1

        request = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        def _probe(ip: str) -> Optional[Dict[str, Any]]:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(timeout)
                    sock.sendto(request, (ip, UDP_TIMER_PORT))
                    resp, _ = sock.recvfrom(4096)
                parsed = json.loads(resp.decode("utf-8"))
                if not isinstance(parsed, dict):
                    return {"ip": ip, "result": "invalid_json"} if include_error else None
                return {
                    "ip": ip,
                    "result": parsed.get("result", "unknown"),
                    "action": parsed.get("action", ""),
                    "message": parsed.get("message", ""),
                    "raw": parsed,
                }
            except Exception as exc:
                if include_error:
                    return {"ip": ip, "result": "timeout_or_error", "message": str(exc)}
                return None

        results: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_probe, ip) for ip in hosts]
            for fut in as_completed(futures):
                item = fut.result()
                if item is not None:
                    results.append(item)

        results.sort(key=lambda x: x["ip"])
        return results

    @staticmethod
    def build_ble_timer_tlv(
        timer_type: TimerType,
        trigger_time: str,
        state_fields: Dict[str, Any],
        weekday: Optional[int] = None,
    ) -> bytes:
        t = AputureController._normalize_timer_type(timer_type)
        tlv = bytearray()

        dt = AputureController._parse_trigger_time(trigger_time)
        if t == "once":
            tlv += AputureController._tlv(0x01, bytes([dt.year >> 8, dt.year & 0xFF, dt.month, dt.day, dt.hour, dt.minute, dt.second]))
        else:
            tlv += AputureController._tlv(0x02, bytes([dt.hour, dt.minute, dt.second]))
            if t == "weekly":
                if weekday is None:
                    weekday = dt.weekday() + 1
                    if weekday == 7:
                        weekday = 0
                if not 0 <= weekday <= 6:
                    raise ValidationError("weekly 模式 weekday 必须为 0..6")
                tlv += AputureController._tlv(0x03, bytes([weekday]))

        for k, v in state_fields.items():
            tlv += AputureController._encode_state_field_tlv(k, v)

        if len(tlv) > 128:
            raise ValidationError("BLE TLV 超过 128 字节限制")

        return bytes(tlv)

    @staticmethod
    def ble_crc16_a001(data: bytes) -> int:
        crc = 0xFFFF
        for b in data:
            crc ^= b
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc & 0xFFFF

    @staticmethod
    def _tlv(tag: int, value: bytes) -> bytes:
        if len(value) > 255:
            raise ValidationError("TLV value 过长")
        return bytes([tag, len(value)]) + value

    @staticmethod
    def _encode_state_field_tlv(key: str, value: Any) -> bytes:
        if key == "power":
            return AputureController._tlv(0x10, bytes([1 if bool(value) else 0]))
        if key == "mode":
            mapping = {"cct": 0, "hsi": 1, "xy": 2}
            if value not in mapping:
                raise ValidationError("mode 必须为 cct/hsi/xy")
            return AputureController._tlv(0x11, bytes([mapping[value]]))
        if key == "level":
            return AputureController._tlv(0x12, bytes([int(value) & 0xFF]))
        if key == "lightness":
            raw = int(round(float(value) * 10))
            return AputureController._tlv(0x13, struct.pack("!H", raw & 0xFFFF))
        if key == "cct":
            return AputureController._tlv(0x14, struct.pack("!H", int(value) & 0xFFFF))
        if key == "gm":
            raw = int(round(float(value) * 100))
            return AputureController._tlv(0x15, struct.pack("!h", raw))
        if key == "hue":
            raw = int(round(float(value) * 10))
            return AputureController._tlv(0x16, struct.pack("!H", raw & 0xFFFF))
        if key == "sat":
            raw = int(round(float(value) * 10))
            return AputureController._tlv(0x17, struct.pack("!H", raw & 0xFFFF))
        if key == "x":
            raw = int(round(float(value) * 10000))
            return AputureController._tlv(0x18, struct.pack("!H", raw & 0xFFFF))
        if key == "y":
            raw = int(round(float(value) * 10000))
            return AputureController._tlv(0x19, struct.pack("!H", raw & 0xFFFF))

        raise ValidationError(f"不支持的状态字段: {key}")

    def _publish_json(self, topic: str, payload: Dict[str, Any], qos: int = 1) -> None:
        if not self._mqtt:
            raise MqttNotConnectedError("MQTT 尚未初始化")
        if not self._mqtt_connected.is_set():
            raise MqttNotConnectedError("MQTT 当前未连接")

        data = json.dumps(payload, ensure_ascii=False)
        with self._mqtt_lock:
            result = self._mqtt.publish(topic, data, qos=qos)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise CommandExecutionError(f"MQTT 发布失败: rc={result.rc}")

    def _on_mqtt_connect(self, client: Any, _userdata: Any, _flags: Dict[str, int], rc: int) -> None:
        self._last_mqtt_rc = rc
        if rc == 0:
            self._mqtt_connected.set()
            client.subscribe(self.timer_reply_topic, qos=1)
            client.subscribe(MQTT_REPORT_TOPIC, qos=1)

    def _on_mqtt_disconnect(self, _client: Any, _userdata: Any, _rc: int) -> None:
        self._mqtt_connected.clear()

    def _on_mqtt_message(self, _client: Any, _userdata: Any, msg: Any) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return

        if msg.topic == self.timer_reply_topic:
            self._timer_reply_queue.put(payload)

    def _drain_timer_reply_queue(self) -> None:
        while True:
            try:
                self._timer_reply_queue.get_nowait()
            except queue.Empty:
                return

    @staticmethod
    def _normalize_mac(mac: str) -> str:
        value = mac.lower().replace(":", "").replace("-", "")
        if len(value) != 12:
            raise ValidationError("MAC 格式无效，应为 12 位十六进制")
        try:
            int(value, 16)
        except ValueError as exc:
            raise ValidationError("MAC 格式无效，应为 12 位十六进制") from exc
        return value

    @staticmethod
    def _normalize_timer_type(timer_type: TimerType) -> str:
        if isinstance(timer_type, int):
            mapping = {0: "once", 1: "daily", 2: "weekly"}
            if timer_type not in mapping:
                raise ValidationError("type 数字仅支持 0/1/2")
            return mapping[timer_type]

        value = str(timer_type).strip().lower()
        if value not in {"once", "daily", "weekly"}:
            raise ValidationError("type 仅支持 once/daily/weekly")
        return value

    @staticmethod
    def _parse_trigger_time(trigger_time: str) -> datetime:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(trigger_time, fmt)
            except ValueError:
                continue
        raise ValidationError("trigger_time 格式必须为 YYYY-MM-DDTHH:MM:SS 或 YYYY-MM-DD HH:MM:SS")

    @staticmethod
    def _validate_light_payload(payload: Dict[str, Any]) -> None:
        allowed = {"power", "mode", "level", "lightness", "cct", "gm", "hue", "sat", "x", "y"}
        unknown = set(payload.keys()) - allowed
        if unknown:
            raise ValidationError(f"未知灯光字段: {sorted(unknown)}")

    @staticmethod
    def _validate_timer_payload(payload: Dict[str, Any]) -> None:
        if "cmd" not in payload:
            raise ValidationError("缺少 cmd")

        cmd = payload["cmd"]
        valid_cmds = {"add_timer", "remove_timer", "clear_timer", "query_timer", "list_timer", "stats_timer"}
        if cmd not in valid_cmds:
            raise ValidationError(f"不支持的 cmd: {cmd}")

        if cmd in {"remove_timer", "query_timer"} and "task_id" not in payload:
            raise ValidationError(f"{cmd} 缺少 task_id")

        if cmd == "add_timer":
            required = {"task_id", "type", "trigger_time"}
            missing = required - set(payload.keys())
            if missing:
                raise ValidationError(f"add_timer 缺少字段: {sorted(missing)}")
            AputureController._normalize_timer_type(payload["type"])
            AputureController._parse_trigger_time(str(payload["trigger_time"]))

            state_keys = {"power", "mode", "level", "lightness", "cct", "gm", "hue", "sat", "x", "y"}
            if not (set(payload.keys()) & state_keys):
                raise ValidationError("add_timer 至少应包含一个状态字段")

    @staticmethod
    def _build_ambl_payload(rgba: Union[bytes, bytearray, Iterable[Tuple[int, int, int, int]]]) -> bytes:
        if isinstance(rgba, (bytes, bytearray)):
            payload = bytes(rgba)
            if len(payload) % 4 != 0:
                raise ValidationError("RGBA 字节长度必须是 4 的倍数")
            return payload

        out = bytearray()
        for r, g, b, a in rgba:
            out.extend([r & 0xFF, g & 0xFF, b & 0xFF, a & 0xFF])
        return bytes(out)


if __name__ == "__main__":
    cfg = ControllerConfig(
        mac="11:22:33:aa:bb:cc",
        device_ip="192.168.1.100",
    )
    ctl = AputureController(cfg)

    # MQTT 示例
    # ctl.connect_mqtt()
    # ctl.send_light_control({"power": True, "mode": "cct", "lightness": 60, "cct": 4300})
    # print(ctl.add_timer_mqtt(101, "once", "2026-04-21T23:00:00", power=True, mode="cct", lightness=75, cct=4500))
    # ctl.disconnect_mqtt()

    # UDP 倒计时示例
    # print(ctl.send_timer_command_udp("stats_timer"))

    # AMBL 示例 (2 通道)
    # ctl.send_ambl_frame(1, [(255, 0, 0, 255), (0, 0, 255, 255)])
