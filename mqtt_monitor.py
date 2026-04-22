"""MQTT Monitor — 作为 broker 内部监控客户端，订阅设备上报主题，追踪在线设备，
支持命令下发及消息记录持久化。

依赖: paho-mqtt >= 1.6
"""
from __future__ import annotations

import json
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import paho.mqtt.client as mqtt  # type: ignore[import-not-found]
    from paho.mqtt.client import CallbackAPIVersion  # type: ignore[import-not-found]

    PAHO_AVAILABLE = True
except ImportError:  # pragma: no cover
    PAHO_AVAILABLE = False

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class DeviceRecord:
    """设备台账条目（持久化到 JSON）"""
    mac: str
    client_id: str = ""
    group_id: str = ""
    firmware_ver: str = ""
    device_sn: str = ""
    remark: str = ""
    status: str = "offline"
    last_seen: str = ""
    last_report: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.client_id:
            self.client_id = f"aputure-{self.mac.replace(':', '').replace('-', '').lower()}"


@dataclass
class MqttMessage:
    """单条 MQTT 消息记录"""
    ts: str
    topic: str
    payload: str
    direction: str = "rx"  # rx = 设备→服务器, tx = 服务器→设备


# ---------------------------------------------------------------------------
# 监控客户端
# ---------------------------------------------------------------------------

class MqttMonitor:
    """以 paho-mqtt 连接到本地/远程 broker，订阅上行主题，追踪设备状态。"""

    MAX_MESSAGES = 500

    # 订阅的上行主题列表
    UPLINK_TOPICS = [
        ("report/data", 1),
        ("iot/device/+/timer_reply", 1),
        ("report/+", 1),
    ]
    # $SYS 连接/断开通知（mosquitto 2.x 支持）
    SYS_TOPICS = [
        ("$SYS/broker/clients/connected", 0),
        ("$SYS/broker/clients/disconnected", 0),
        ("$SYS/broker/clients/total", 0),
    ]

    def __init__(
        self,
        store_path: str,
        on_message_cb: Optional[Callable[["MqttMessage"], None]] = None,
    ) -> None:
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.on_message_cb = on_message_cb

        self._client: Optional[Any] = None
        self._connected = False
        self._lock = threading.Lock()
        self._pub_events: Dict[int, Dict[str, Any]] = {}
        self._last_disconnect_rc: Optional[int] = None

        self.messages: deque[MqttMessage] = deque(maxlen=self.MAX_MESSAGES)
        self.devices: Dict[str, DeviceRecord] = {}  # mac → DeviceRecord
        self.sys_stats: Dict[str, str] = {}  # $SYS key → value

        self._load_devices()

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def _load_devices(self) -> None:
        if self.store_path.exists():
            try:
                raw = json.loads(self.store_path.read_text(encoding="utf-8"))
                for mac, d in raw.items():
                    # 兼容旧格式（可能有额外字段）
                    valid = {k: v for k, v in d.items() if k in DeviceRecord.__dataclass_fields__}
                    self.devices[mac] = DeviceRecord(**valid)
            except Exception:
                pass

    def save_devices(self) -> None:
        data: Dict[str, Any] = {}
        with self._lock:
            for mac, rec in self.devices.items():
                data[mac] = asdict(rec)
        self.store_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    def connect(
        self,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        use_tls: bool = False,
        client_id: str = "aputure-monitor-001",
        timeout_s: float = 3.0,
    ) -> Tuple[bool, str]:
        if not PAHO_AVAILABLE:
            return False, "paho-mqtt 未安装，请运行: pip install paho-mqtt"
        if self.is_connected():
            return True, "监控客户端已连接"

        try:
            try:
                client = mqtt.Client(
                    callback_api_version=CallbackAPIVersion.VERSION2,
                    client_id=client_id,
                    clean_session=True,
                )
            except Exception:
                # paho < 2.0 fallback
                client = mqtt.Client(client_id=client_id, clean_session=True)  # type: ignore[call-arg]
            if username:
                client.username_pw_set(username, password or "")
            if use_tls:
                client.tls_set()

            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            client.on_publish = self._on_publish

            client.connect(host, int(port), keepalive=60)
            client.loop_start()

            deadline = time.time() + timeout_s
            while time.time() < deadline:
                if self._connected:
                    break
                time.sleep(0.05)

            if not self._connected:
                client.loop_stop()
                return False, f"连接超时（{timeout_s}s）: {host}:{port}"

            self._client = client
            return True, f"已连接到 {host}:{port}，开始监听设备上报"
        except Exception as exc:
            return False, f"连接失败: {exc}"

    def disconnect(self) -> Tuple[bool, str]:
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        self._connected = False
        return True, "已断开监控连接"

    def status_text(self) -> str:
        if self.is_connected():
            return f"已连接（在线设备 {self.get_online_count()} 台）"
        return "未连接"

    # ------------------------------------------------------------------
    # paho 回调
    # ------------------------------------------------------------------

    def _on_connect(self, client: Any, userdata: Any, flags: Any, rc: Any, properties: Any = None) -> None:
        rc_val = rc if isinstance(rc, int) else getattr(rc, 'value', 0)
        if rc_val == 0:
            self._connected = True
            # 订阅上行及 $SYS 主题
            for topic, qos in self.UPLINK_TOPICS + self.SYS_TOPICS:
                client.subscribe(topic, qos=qos)
        else:
            self._connected = False

    def _on_disconnect(self, client: Any, userdata: Any, disconnect_flags: Any = None, rc: Any = None, properties: Any = None) -> None:
        if rc is None:
            self._last_disconnect_rc = None
        elif isinstance(rc, int):
            self._last_disconnect_rc = rc
        else:
            self._last_disconnect_rc = int(getattr(rc, "value", 0))
        self._connected = False

    def _on_publish(self, client: Any, userdata: Any, mid: int, reason_code: Any = None, properties: Any = None) -> None:
        rc_val = 0
        if reason_code is None:
            rc_val = 0
        elif isinstance(reason_code, int):
            rc_val = reason_code
        else:
            rc_val = int(getattr(reason_code, "value", 0))

        with self._lock:
            ev = self._pub_events.get(int(mid), {"done": False, "rc": None})
            ev["done"] = True
            ev["rc"] = rc_val
            self._pub_events[int(mid)] = ev

    def _on_message(self, client: Any, userdata: Any, msg: Any) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            payload_str = msg.payload.decode("utf-8", errors="replace")
        except Exception:
            payload_str = repr(msg.payload)

        # $SYS 统计
        if msg.topic.startswith("$SYS/"):
            key = msg.topic.split("/", 2)[-1]
            with self._lock:
                self.sys_stats[key] = payload_str
            return

        m = MqttMessage(ts=ts, topic=msg.topic, payload=payload_str, direction="rx")
        with self._lock:
            self.messages.appendleft(m)

        # 尝试从主题/负载中提取 MAC
        mac = self._extract_mac(msg.topic, payload_str)
        if mac:
            with self._lock:
                rec = self.devices.get(
                    mac, DeviceRecord(mac=mac, client_id=f"aputure-{mac}")
                )
                rec.last_seen = ts
                rec.status = "online"
                if msg.topic.startswith("report/"):
                    rec.last_report = payload_str[:300]
                self.devices[mac] = rec
            self.save_devices()

        if self.on_message_cb:
            try:
                self.on_message_cb(m)
            except Exception:
                pass

    @staticmethod
    def _extract_mac(topic: str, payload: str) -> Optional[str]:
        """从主题或 JSON 负载中提取 12 位 MAC（小写无分隔符）"""
        parts = topic.split("/")
        # iot/device/{mac}/... 形式
        if len(parts) >= 3 and parts[0] == "iot" and parts[1] == "device":
            candidate = parts[2]
            if len(candidate) == 12 and all(c in "0123456789abcdefABCDEF" for c in candidate):
                return candidate.lower()
        # report/data → 从 JSON 读
        try:
            d = json.loads(payload)
            for key in ("mac", "device_mac", "deviceMac"):
                raw = d.get(key, "")
                if isinstance(raw, str):
                    clean = raw.replace(":", "").replace("-", "").lower()
                    if len(clean) == 12:
                        return clean
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # 发布命令
    # ------------------------------------------------------------------

    def publish(self, topic: str, payload: str, qos: int = 1) -> Tuple[bool, str]:
        if not self.is_connected() or self._client is None:
            return False, "监控客户端未连接，请先连接"
        t = str(topic).strip()
        if not t:
            return False, "发布失败: topic 不能为空"
        try:
            info = self._client.publish(t, payload, qos=int(qos))
            if int(getattr(info, "rc", 0)) != 0:
                return False, f"发布失败: publish rc={getattr(info, 'rc', 'unknown')}"

            mid = int(getattr(info, "mid", 0))
            if int(qos) > 0 and mid > 0:
                with self._lock:
                    self._pub_events.setdefault(mid, {"done": False, "rc": None})

                deadline = time.time() + 3.0
                while time.time() < deadline:
                    with self._lock:
                        ev = self._pub_events.get(mid)
                        done = bool(ev and ev.get("done"))
                        rc_raw = ev.get("rc", 0) if ev else 0
                        rc_val = 0 if rc_raw is None else int(rc_raw)
                    if done:
                        with self._lock:
                            self._pub_events.pop(mid, None)
                        if rc_val != 0:
                            return False, f"发布失败: PUBACK rc={rc_val}"
                        break
                    time.sleep(0.02)
                else:
                    with self._lock:
                        self._pub_events.pop(mid, None)
                    return False, "发布失败: 等待 PUBACK 超时，消息可能未被 broker 接收"

            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            m = MqttMessage(ts=ts, topic=t, payload=payload, direction="tx")
            with self._lock:
                self.messages.appendleft(m)
            return True, f"发布成功 (mid={mid})"
        except Exception as exc:
            return False, f"发布失败: {exc}"

    # ------------------------------------------------------------------
    # 查询接口
    # ------------------------------------------------------------------

    def get_messages(self, limit: int = 100) -> List[MqttMessage]:
        with self._lock:
            return list(self.messages)[:limit]

    def get_devices(self) -> List[DeviceRecord]:
        with self._lock:
            return list(self.devices.values())

    def get_online_count(self) -> int:
        with self._lock:
            return sum(1 for r in self.devices.values() if r.status == "online")

    # ------------------------------------------------------------------
    # 设备台账 CRUD
    # ------------------------------------------------------------------

    def add_device(self, mac: str, **kwargs: Any) -> DeviceRecord:
        mac = mac.replace(":", "").replace("-", "").lower()
        with self._lock:
            rec = self.devices.get(mac, DeviceRecord(mac=mac))
            for k, v in kwargs.items():
                if k in DeviceRecord.__dataclass_fields__:
                    setattr(rec, k, v)
            self.devices[mac] = rec
        self.save_devices()
        return rec

    def remove_device(self, mac: str) -> bool:
        mac = mac.replace(":", "").replace("-", "").lower()
        with self._lock:
            removed = mac in self.devices
            if removed:
                del self.devices[mac]
        if removed:
            self.save_devices()
        return removed

    def mark_offline(self, mac: str) -> None:
        mac = mac.replace(":", "").replace("-", "").lower()
        with self._lock:
            if mac in self.devices:
                self.devices[mac].status = "offline"
        self.save_devices()

    def mark_all_offline(self) -> None:
        with self._lock:
            for rec in self.devices.values():
                rec.status = "offline"
        self.save_devices()
