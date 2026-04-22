from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class MqttServerConfig:
    listener_host: str = "0.0.0.0"
    listener_port: int = 8883
    allow_anonymous: bool = False
    password_file: str = ""
    acl_file: str = ""
    tls_enabled: bool = True
    cafile: str = ""
    certfile: str = ""
    keyfile: str = ""


class MqttServerManager:
    def __init__(self, workspace: str) -> None:
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.config_path = self.workspace / "mosquitto.conf"
        self.log_path = self.workspace / "mosquitto.log"
        self._proc: Optional[subprocess.Popen[str]] = None

    def mosquitto_exists(self) -> bool:
        return shutil.which("mosquitto") is not None

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def write_config(self, cfg: MqttServerConfig) -> None:
        lines = [
            "persistence false",
            f"listener {int(cfg.listener_port)} {cfg.listener_host}",
            f"allow_anonymous {'true' if cfg.allow_anonymous else 'false'}",
            "log_dest file " + str(self.log_path),
            "log_type all",
            "connection_messages true",
        ]

        if cfg.tls_enabled:
            if cfg.cafile.strip():
                lines.append(f"cafile {cfg.cafile.strip()}")
            if cfg.certfile.strip():
                lines.append(f"certfile {cfg.certfile.strip()}")
            if cfg.keyfile.strip():
                lines.append(f"keyfile {cfg.keyfile.strip()}")
            lines.append("tls_version tlsv1.2")

        if cfg.password_file.strip():
            lines.append(f"password_file {cfg.password_file.strip()}")
        if cfg.acl_file.strip():
            acl = Path(cfg.acl_file.strip())
            acl.parent.mkdir(parents=True, exist_ok=True)
            if not acl.exists():
                acl.write_text("", encoding="utf-8")
            lines.append(f"acl_file {acl}")

        self.config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_acl_from_macs(self, macs: Iterable[str], out_path: Optional[str] = None) -> Path:
        """
        生成 ACL 文件（与 server.md 的 topic 规则一致）。
        约定：username == client_id == aputure-{mac}
        """
        target = Path(out_path) if out_path else (self.workspace / "mosquitto.acl")
        rules: list[str] = []
        for raw in macs:
            mac = str(raw).strip().lower().replace(":", "").replace("-", "")
            if len(mac) != 12:
                continue
            client_id = f"aputure-{mac}"
            rules.extend(
                [
                    f"user {client_id}",
                    f"topic read iot/device/{mac}/down",
                    f"topic read iot/device/{mac}/timer",
                    "topic read iot/device/group/down",
                    "topic read iot/device/group/timer",
                    "topic read iot/device/all/down",
                    "topic read iot/device/all/timer",
                    "topic write report/data",
                    f"topic write iot/device/{mac}/timer_reply",
                    "",
                ]
            )

        # 默认兜底拒绝（mosquitto ACL 没有显式 deny all，未命中即拒绝）
        target.write_text("\n".join(rules).strip() + "\n", encoding="utf-8")
        return target

    def can_bind(self, host: str, port: int) -> tuple[bool, str]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, int(port)))
            return True, "ok"
        except OSError as exc:
            return False, str(exc)
        finally:
            sock.close()

    def start(self, cfg: MqttServerConfig) -> tuple[bool, str]:
        if not self.mosquitto_exists():
            return False, "未找到 mosquitto，可先安装: sudo apt install mosquitto"

        if self.is_running():
            return True, "MQTT Server 已在运行"

        if cfg.tls_enabled:
            for label, p in (("cafile", cfg.cafile), ("certfile", cfg.certfile), ("keyfile", cfg.keyfile)):
                pp = Path(str(p).strip())
                if not pp.exists():
                    return False, f"TLS 配置无效: {label} 不存在 -> {pp}"

        can_bind, bind_msg = self.can_bind(cfg.listener_host, int(cfg.listener_port))
        if not can_bind:
            return False, f"端口占用，无法绑定 {cfg.listener_host}:{cfg.listener_port}，错误: {bind_msg}"

        self.write_config(cfg)

        log_fp = self.log_path.open("a", encoding="utf-8")
        self._proc = subprocess.Popen(
            ["mosquitto", "-c", str(self.config_path), "-v"],
            cwd=str(self.workspace),
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            text=True,
        )

        time.sleep(0.4)
        if self._proc.poll() is not None:
            code = self._proc.returncode
            self._proc = None
            tail = self.tail_logs(max_lines=30)
            return False, f"MQTT Server 启动失败，exit_code={code}\n{tail}"

        return True, f"MQTT Server 启动中 (pid={self._proc.pid})"

    def stop(self) -> tuple[bool, str]:
        if not self.is_running():
            self._proc = None
            return True, "MQTT Server 未运行"

        assert self._proc is not None
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=3)

        self._proc = None
        return True, "MQTT Server 已停止"

    def status_text(self) -> str:
        if self.is_running():
            assert self._proc is not None
            return f"运行中 (pid={self._proc.pid})"
        return "未运行"

    def check_listener(self, host: str, port: int, timeout: float = 1.0) -> tuple[bool, str]:
        try:
            with socket.create_connection((host, int(port)), timeout=timeout):
                return True, "端口可连接"
        except Exception as exc:
            return False, str(exc)

    def tail_logs(self, max_lines: int = 200) -> str:
        if not self.log_path.exists():
            return ""
        lines = self.log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(lines[-max_lines:])
