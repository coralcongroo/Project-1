from __future__ import annotations

from typing import Any, Dict, List, Optional

from controller import AputureController, ControllerConfig
from device_manager import DeviceListManager
from sdk import AputureSDK, LightState


class BatchDeviceController:
    """批量设备控制"""

    def __init__(self, devices: List[Dict[str, Any]]) -> None:
        self.devices = devices

    @staticmethod
    def from_file(filepath: str) -> BatchDeviceController:
        """从设备列表文件加载"""
        mgr = DeviceListManager(filepath)
        devices = mgr.load()
        return BatchDeviceController(devices)

    def get_ips(self) -> List[str]:
        """获取所有 IP"""
        return [d.get("ip") for d in self.devices if d.get("ip")]

    def get_by_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        """按 IP 获取设备信息"""
        for d in self.devices:
            if d.get("ip") == ip:
                return d
        return None

    def batch_light_control(
        self,
        ips: List[str],
        state: Dict[str, Any],
        mqtt_host: str = "broker.emqx.io",
        mqtt_port: int = 8883,
        mqtt_tls: bool = True,
        timeout: float = 3.0,
        skip_errors: bool = True,
    ) -> Dict[str, Any]:
        """对多个设备执行灯光控制"""
        results: Dict[str, Any] = {}
        for ip in ips:
            try:
                cfg = ControllerConfig(
                    mac="00:00:00:00:00:00",
                    device_ip=ip,
                    mqtt_host=mqtt_host,
                    mqtt_port=mqtt_port,
                    mqtt_tls=mqtt_tls,
                )
                ctl = AputureController(cfg)
                ctl.connect_mqtt()
                try:
                    ctl.send_light_control(state)
                    results[ip] = {"result": "ok"}
                finally:
                    ctl.disconnect_mqtt()
            except Exception as exc:
                if skip_errors:
                    results[ip] = {"result": "error", "message": str(exc)}
                else:
                    raise

        return {"result": "batch_ok", "total": len(ips), "results": results}

    def batch_timer_command(
        self,
        ips: List[str],
        cmd: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 1.5,
        skip_errors: bool = True,
    ) -> Dict[str, Any]:
        """对多个设备执行 UDP 倒计时命令"""
        results: Dict[str, Any] = {}
        for ip in ips:
            try:
                cfg = ControllerConfig(mac="00:00:00:00:00:00", device_ip=ip)
                ctl = AputureController(cfg)
                result = ctl.send_timer_command_udp(cmd, payload=payload, timeout=timeout)
                results[ip] = result
            except Exception as exc:
                if skip_errors:
                    results[ip] = {"result": "error", "message": str(exc)}
                else:
                    raise

        return {"result": "batch_ok", "total": len(ips), "results": results}
