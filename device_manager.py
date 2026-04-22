from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DeviceInfo:
    """设备信息"""
    ip: str
    mac: Optional[str] = None
    name: Optional[str] = None
    result: str = "unknown"
    action: str = ""
    message: str = ""
    timestamp: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> DeviceInfo:
        return DeviceInfo(**data)


class DeviceListManager:
    """设备列表管理（保存/加载 JSON）"""

    def __init__(self, filepath: str = "devices.json") -> None:
        self.filepath = Path(filepath)

    def save(self, devices: List[Dict[str, Any]] | List[DeviceInfo]) -> None:
        """保存设备列表到 JSON"""
        if not devices:
            raise ValueError("设备列表为空")

        items = []
        for item in devices:
            if isinstance(item, DeviceInfo):
                items.append(item.to_dict())
            else:
                items.append(item)

        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump({"devices": items, "count": len(items)}, f, ensure_ascii=False, indent=2)

    def load(self) -> List[Dict[str, Any]]:
        """从 JSON 加载设备列表"""
        if not self.filepath.exists():
            raise FileNotFoundError(f"文件不存在: {self.filepath}")

        with open(self.filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or "devices" not in data:
            raise ValueError("JSON 格式无效，应包含 devices 字段")

        return data.get("devices", [])

    def append(self, devices: List[Dict[str, Any]] | List[DeviceInfo]) -> None:
        """追加到现有列表"""
        try:
            existing = self.load()
        except FileNotFoundError:
            existing = []

        for item in devices:
            if isinstance(item, DeviceInfo):
                existing.append(item.to_dict())
            else:
                existing.append(item)

        self.save(existing)

    def clear(self) -> None:
        """清空列表"""
        if self.filepath.exists():
            self.filepath.unlink()

    def list_ips(self) -> List[str]:
        """获取所有 IP 列表"""
        devices = self.load()
        return [dev.get("ip") for dev in devices if dev.get("ip")]

    def get_by_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        """按 IP 查找"""
        devices = self.load()
        for dev in devices:
            if dev.get("ip") == ip:
                return dev
        return None

    def update_mac(self, ip: str, mac: str) -> None:
        """更新设备 MAC"""
        devices = self.load()
        for dev in devices:
            if dev.get("ip") == ip:
                dev["mac"] = mac
        self.save(devices)

    def remove(self, ip: str) -> None:
        """删除设备"""
        devices = self.load()
        devices = [d for d in devices if d.get("ip") != ip]
        self.save(devices)

    def rename(self, ip: str, name: str) -> None:
        """重命名设备"""
        devices = self.load()
        for dev in devices:
            if dev.get("ip") == ip:
                dev["name"] = name
        self.save(devices)
