from __future__ import annotations

import itertools
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from controller import AputureController, ControllerConfig


class SDKError(Exception):
    pass


class DeviceCommandError(SDKError):
    pass


class UnsupportedModeError(SDKError):
    pass


@dataclass
class LightState:
    power: Optional[bool] = None
    mode: Optional[str] = None
    level: Optional[int] = None
    lightness: Optional[float] = None
    cct: Optional[int] = None
    gm: Optional[float] = None
    hue: Optional[float] = None
    sat: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None

    def to_payload(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for k, v in self.__dict__.items():
            if v is not None:
                data[k] = v
        return data


@dataclass
class TimerTask:
    task_id: int
    timer_type: str
    trigger_time: str
    state: LightState

    def to_payload(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "type": self.timer_type,
            "trigger_time": self.trigger_time,
            **self.state.to_payload(),
        }


class TaskIdGenerator:
    def __init__(self, start: int = 1000) -> None:
        self._counter = itertools.count(start)
        self._lock = threading.Lock()

    def next_id(self) -> int:
        with self._lock:
            return next(self._counter)


class AputureSDK:
    def __init__(self, config: ControllerConfig) -> None:
        self.controller = AputureController(config)
        self.task_id_gen = TaskIdGenerator()
        self.task_map: Dict[int, TimerTask] = {}

    def connect(self) -> None:
        # Server-only mode: MQTT client connection disabled
        return None

    def disconnect(self) -> None:
        # Server-only mode: MQTT client connection disabled
        return None

    def set_light(self, state: LightState) -> None:
        raise UnsupportedModeError("当前为 MQTT Server 模式，SDK 不提供 MQTT 客户端控灯")

    def create_timer(
        self,
        timer_type: str,
        trigger_time: str,
        state: LightState,
        transport: str = "udp",
        task_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        tid = task_id if task_id is not None else self.task_id_gen.next_id()
        task = TimerTask(task_id=tid, timer_type=timer_type, trigger_time=trigger_time, state=state)

        if transport == "udp":
            result = self.controller.send_timer_command_udp("add_timer", payload=task.to_payload())
        else:
            raise UnsupportedModeError("当前模式仅支持 UDP")

        self._ensure_ok("add_timer", result)
        if result.get("result") == "ok":
            self.task_map[tid] = task
        return result

    def remove_timer(self, task_id: int, transport: str = "udp") -> Dict[str, Any]:
        if transport == "udp":
            result = self.controller.send_timer_command_udp("remove_timer", payload={"task_id": task_id})
        else:
            raise UnsupportedModeError("当前模式仅支持 UDP")

        self._ensure_ok("remove_timer", result)
        if result.get("result") == "ok":
            self.task_map.pop(task_id, None)
        return result

    def query_timer(self, task_id: int, transport: str = "udp") -> Dict[str, Any]:
        if transport == "udp":
            result = self.controller.send_timer_command_udp("query_timer", payload={"task_id": task_id})
            self._ensure_ok("query_timer", result)
            return result
        raise UnsupportedModeError("当前模式仅支持 UDP")

    def list_timers(self, transport: str = "udp") -> Dict[str, Any]:
        if transport == "udp":
            result = self.controller.send_timer_command_udp("list_timer")
            self._ensure_ok("list_timer", result)
            return result
        raise UnsupportedModeError("当前模式仅支持 UDP")

    def stats_timers(self, transport: str = "udp") -> Dict[str, Any]:
        if transport == "udp":
            result = self.controller.send_timer_command_udp("stats_timer")
            self._ensure_ok("stats_timer", result)
            return result
        raise UnsupportedModeError("当前模式仅支持 UDP")

    def clear_timers(self, transport: str = "udp") -> Dict[str, Any]:
        if transport == "udp":
            result = self.controller.send_timer_command_udp("clear_timer")
        else:
            raise UnsupportedModeError("当前模式仅支持 UDP")

        self._ensure_ok("clear_timer", result)
        if result.get("result") == "ok":
            self.task_map.clear()
        return result

    def batch_create_timers(
        self,
        items: List[Tuple[str, str, LightState]],
        transport: str = "udp",
        retries: int = 2,
        retry_delay: float = 0.3,
        rollback_on_error: bool = True,
    ) -> Dict[str, Any]:
        created_ids: List[int] = []
        details: List[Dict[str, Any]] = []

        for timer_type, trigger_time, state in items:
            tid = self.task_id_gen.next_id()
            attempt = 0
            while True:
                attempt += 1
                try:
                    result = self.create_timer(
                        timer_type=timer_type,
                        trigger_time=trigger_time,
                        state=state,
                        transport=transport,
                        task_id=tid,
                    )
                    created_ids.append(tid)
                    details.append({"task_id": tid, "result": result, "attempt": attempt})
                    break
                except Exception as exc:
                    if attempt <= retries:
                        time.sleep(retry_delay)
                        continue

                    if rollback_on_error:
                        rollback_errors: List[str] = []
                        for created_id in created_ids:
                            try:
                                self.remove_timer(created_id, transport=transport)
                            except Exception as rb_exc:
                                rollback_errors.append(f"task_id={created_id}, err={rb_exc}")

                        raise DeviceCommandError(
                            f"批量创建失败并已回滚，失败task_id={tid}, 错误={exc}, 回滚异常={rollback_errors}"
                        ) from exc

                    raise DeviceCommandError(f"批量创建失败，失败task_id={tid}, 错误={exc}") from exc

        return {
            "result": "ok",
            "count": len(created_ids),
            "task_ids": created_ids,
            "details": details,
        }

    def batch_remove_timers(
        self,
        task_ids: List[int],
        transport: str = "udp",
        retries: int = 2,
        retry_delay: float = 0.3,
    ) -> Dict[str, Any]:
        removed_ids: List[int] = []
        failed: List[Dict[str, Any]] = []

        for task_id in task_ids:
            attempt = 0
            last_error: Optional[Exception] = None
            while attempt <= retries:
                attempt += 1
                try:
                    result = self.remove_timer(task_id, transport=transport)
                    removed_ids.append(task_id)
                    failed_result = result.get("result")
                    if failed_result != "ok":
                        raise DeviceCommandError(f"task_id={task_id}, result={failed_result}")
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt <= retries:
                        time.sleep(retry_delay)
                        continue
                    failed.append({"task_id": task_id, "error": str(last_error), "attempt": attempt})

        if failed:
            return {
                "result": "partial",
                "removed": removed_ids,
                "failed": failed,
            }

        return {
            "result": "ok",
            "removed": removed_ids,
            "failed": [],
        }

    @staticmethod
    def _ensure_ok(action: str, result: Dict[str, Any]) -> None:
        if result.get("result") == "ok":
            return
        message = str(result.get("message", "unknown error"))
        device_action = str(result.get("action", action))
        raise DeviceCommandError(f"命令失败: action={device_action}, message={message}")
