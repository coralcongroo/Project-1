#!/usr/bin/env python3
"""
自动调试设置工具 — 一键配置和测试 MQTT Server + Monitor + Device
用法: python debug_setup.py
"""
import subprocess
import sys
import time
import json
import os
from pathlib import Path
from typing import Tuple

# 彩色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_step(n: int, title: str) -> None:
    print(f"\n{Colors.HEADER}{Colors.BOLD}[步骤 {n}] {title}{Colors.ENDC}")

def print_ok(msg: str) -> None:
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_warn(msg: str) -> None:
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

def print_err(msg: str) -> None:
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def print_info(msg: str) -> None:
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")

def check_command(cmd: str) -> bool:
    """检查命令是否存在"""
    result = subprocess.run(['which', cmd], capture_output=True)
    return result.returncode == 0

def check_python_package(pkg: str) -> bool:
    """检查 Python 包是否安装"""
    try:
        __import__(pkg)
        return True
    except ImportError:
        return False

def run_command(cmd: list, timeout: float = 5) -> Tuple[bool, str]:
    """运行命令，返回成功状态和输出"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"超时（>{timeout}s）"
    except Exception as e:
        return False, str(e)

# ================================================================
# 主流程
# ================================================================

def main() -> None:
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}")
    print("MQTT Server & Monitor 自动调试设置")
    print(f"{'='*60}{Colors.ENDC}\n")

    workspace = Path(__file__).resolve().parent
    os.chdir(workspace)

    # ════════════════════════════════════════════════════════════
    # 步骤 1: 检查依赖
    # ════════════════════════════════════════════════════════════
    print_step(1, "检查系统依赖")
    
    missing = []
    
    if not check_command('mosquitto'):
        print_err("mosquitto 未安装")
        missing.append('mosquitto')
        print_info("安装: sudo apt install mosquitto")
    else:
        print_ok("mosquitto 已安装")
    
    if not check_python_package('paho'):
        print_err("paho-mqtt Python 包未安装")
        missing.append('paho-mqtt')
        print_info("安装: pip install paho-mqtt>=1.6.1")
    else:
        print_ok("paho-mqtt 已安装")
    
    if missing:
        print_err(f"缺少依赖: {', '.join(missing)}")
        print_info("请先安装上述依赖，然后重新运行此脚本")
        sys.exit(1)

    # ════════════════════════════════════════════════════════════
    # 步骤 2: 初始化配置
    # ════════════════════════════════════════════════════════════
    print_step(2, "初始化 MQTT Server 配置")
    
    from mqtt_server import MqttServerConfig, MqttServerManager
    
    mgr = MqttServerManager(".mqtt_server")
    print_ok(f"工作目录: {mgr.workspace}")
    
    # 停止已运行的 mosquitto
    run_command(['pkill', '-9', 'mosquitto'])
    time.sleep(0.3)
    
    # 启动 Server
    cfg = MqttServerConfig(
        listener_host="0.0.0.0",
        listener_port=8883,
        allow_anonymous=True,
        acl_file="",
        tls_enabled=False,
        local_plain_port=1883,  # 本地 1883 供监控
    )
    
    ok, msg = mgr.start(cfg)
    if not ok:
        print_err(f"Server 启动失败: {msg}")
        sys.exit(1)
    
    time.sleep(1)
    print_ok(f"MQTT Server 已启动 (port 8883 + local 1883)")
    print_info(f"日志: {mgr.log_path}")

    # ════════════════════════════════════════════════════════════
    # 步骤 3: 验证 Server 监听
    # ════════════════════════════════════════════════════════════
    print_step(3, "验证 Server 监听")
    
    ok, msg = mgr.check_listener("127.0.0.1", 1883, timeout=1)
    if ok:
        print_ok("本地 1883 可连接")
    else:
        print_err(f"本地 1883 检测失败: {msg}")
        sys.exit(1)
    
    ok, msg = mgr.check_listener("0.0.0.0", 8883, timeout=1)
    if ok:
        print_ok("外网 8883 可连接")
    else:
        print_warn(f"外网 8883 检测失败（本地测试可忽略）")

    # ════════════════════════════════════════════════════════════
    # 步骤 4: 启动监控客户端
    # ════════════════════════════════════════════════════════════
    print_step(4, "启动监控客户端")
    
    from mqtt_monitor import MqttMonitor
    
    store_path = str(workspace / ".mqtt_server" / "devices.json")
    mon = MqttMonitor(store_path)
    ok, msg = mon.connect(host='127.0.0.1', port=1883, client_id='debug-monitor')
    if not ok:
        print_err(f"监控连接失败: {msg}")
        sys.exit(1)
    
    print_ok(msg)
    time.sleep(0.5)

    # ════════════════════════════════════════════════════════════
    # 步骤 5: 添加示例设备到台账
    # ════════════════════════════════════════════════════════════
    print_step(5, "初始化设备台账")
    
    sample_devices = [
        {"mac": "112233aabbcc", "device_sn": "DEV001", "firmware_ver": "v1.0", "group_id": "group1", "remark": "示例设备1"},
        {"mac": "aabbccdd1122", "device_sn": "DEV002", "firmware_ver": "v1.0", "group_id": "group1", "remark": "示例设备2"},
    ]
    
    for dev in sample_devices:
        mon.add_device(
            mac=dev["mac"],
            device_sn=dev["device_sn"],
            firmware_ver=dev["firmware_ver"],
            group_id=dev["group_id"],
            remark=dev["remark"],
        )
        print_ok(f"已添加设备: {dev['mac']} ({dev['device_sn']})")

    # ════════════════════════════════════════════════════════════
    # 步骤 6: 模拟设备上报并测试命令下发
    # ════════════════════════════════════════════════════════════
    print_step(6, "模拟设备并测试命令下发")
    
    import paho.mqtt.client as mqtt
    from paho.mqtt.client import CallbackAPIVersion
    import threading
    
    test_results = {
        "command_sent": False,
        "command_received": False,
        "device_reported": False,
        "device_registered": False,
    }
    
    def simulate_device():
        """模拟一个 MQTT 设备"""
        try:
            dev = mqtt.Client(
                callback_api_version=CallbackAPIVersion.VERSION2,
                client_id='aputure-112233aabbcc'
            )
            
            def on_connect(c, u, f, rc, props=None):
                rc_val = rc if isinstance(rc, int) else getattr(rc, 'value', 0)
                if rc_val == 0:
                    c.subscribe('iot/device/112233aabbcc/down', qos=1)
                    c.subscribe('iot/device/group/down', qos=1)
                    c.subscribe('iot/device/all/down', qos=1)
            
            def on_message(c, u, m):
                test_results["command_received"] = True
                # 上报确认
                report = json.dumps({
                    "mac": "112233aabbcc",
                    "status": "online",
                    "cmd_acked": True
                })
                c.publish('report/data', report, qos=1)
            
            dev.on_connect = on_connect
            dev.on_message = on_message
            dev.connect('127.0.0.1', 1883, keepalive=60)
            dev.loop_start()
            time.sleep(2.5)
            dev.loop_stop()
            dev.disconnect()
        except Exception as e:
            print_err(f"设备模拟失败: {e}")
    
    # 启动设备线程
    dev_thread = threading.Thread(target=simulate_device, daemon=True)
    dev_thread.start()
    
    # 等待设备连接
    time.sleep(0.5)
    
    # 发送命令
    print_info("发送测试命令...")
    ok, msg = mon.publish(
        'iot/device/112233aabbcc/down',
        json.dumps({"power": True, "lightness": 50}),
        qos=1
    )
    test_results["command_sent"] = ok
    if ok:
        print_ok("命令已发布")
    else:
        print_err(f"命令发布失败: {msg}")
    
    # 等待设备响应
    time.sleep(2)
    dev_thread.join(timeout=1)
    
    # 检查设备是否被注册
    devices = mon.get_devices()
    if any(d.mac == "112233aabbcc" for d in devices):
        test_results["device_registered"] = True
    
    # 检查是否接收到设备上报
    rx_msgs = [m for m in mon.get_messages(50) if m.direction == 'rx' and 'report' in m.topic]
    if rx_msgs:
        test_results["device_reported"] = True

    # ════════════════════════════════════════════════════════════
    # 步骤 7: 输出测试报告
    # ════════════════════════════════════════════════════════════
    print_step(7, "测试报告")
    
    print(f"\n{Colors.BOLD}命令下发测试:{Colors.ENDC}")
    print(f"  {'✓' if test_results['command_sent'] else '✗'} 命令发布")
    print(f"  {'✓' if test_results['command_received'] else '✗'} 设备接收")
    
    print(f"\n{Colors.BOLD}设备管理测试:{Colors.ENDC}")
    print(f"  {'✓' if test_results['device_registered'] else '✗'} 设备自动入库")
    print(f"  {'✓' if test_results['device_reported'] else '✗'} 设备上报数据")
    
    print(f"\n{Colors.BOLD}设备台账:{Colors.ENDC}")
    devices = mon.get_devices()
    print(f"  总计: {len(devices)} 台设备")
    for d in devices:
        print(f"    - {d.mac}: {d.status} (最近: {d.last_seen})")
    
    print(f"\n{Colors.BOLD}消息流水:{Colors.ENDC}")
    msgs = mon.get_messages(10)
    print(f"  总计: {len(mon.messages)} 条消息，显示最近 {min(10, len(msgs))} 条:")
    for m in msgs[:10]:
        dir_str = "TX ⬆" if m.direction == "tx" else "RX ⬇"
        print(f"    [{m.ts}] {dir_str} {m.topic}: {m.payload[:60]}")

    # ════════════════════════════════════════════════════════════
    # 步骤 8: 生成配置信息
    # ════════════════════════════════════════════════════════════
    print_step(8, "配置信息")
    
    config_info = {
        "server": {
            "host": "0.0.0.0",
            "port": 8883,
            "local_plain_port": 1883,
            "tls_enabled": False,
            "allow_anonymous": True,
        },
        "monitor": {
            "host": "127.0.0.1",
            "port": 1883,
        },
        "workspace": str(mgr.workspace),
        "config_file": str(mgr.config_path),
        "log_file": str(mgr.log_path),
        "devices_file": store_path,
    }
    
    print(f"\n{Colors.BOLD}Server 配置:{Colors.ENDC}")
    print(f"  监听地址: {config_info['server']['host']}:{config_info['server']['port']}")
    print(f"  本地端口: 127.0.0.1:{config_info['server']['local_plain_port']}")
    print(f"  TLS: {'启用' if config_info['server']['tls_enabled'] else '禁用'}")
    
    print(f"\n{Colors.BOLD}文件位置:{Colors.ENDC}")
    print(f"  工作目录: {config_info['workspace']}")
    print(f"  配置文件: {config_info['config_file']}")
    print(f"  日志文件: {config_info['log_file']}")
    print(f"  设备台账: {config_info['devices_file']}")

    # ════════════════════════════════════════════════════════════
    # 完成
    # ════════════════════════════════════════════════════════════
    mon.disconnect()
    
    all_ok = all(test_results.values())
    print(f"\n{Colors.BOLD}{'='*60}")
    if all_ok:
        print(f"{Colors.OKGREEN}✓ 自动调试设置完成！所有测试通过{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}⚠ 自动调试设置完成，但部分测试未通过{Colors.ENDC}")
    print(f"{'='*60}{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}后续步骤:{Colors.ENDC}")
    print(f"  1. 启动 Streamlit UI:  python -m streamlit run ui_app.py")
    print(f"  2. 在浏览器中打开:     http://localhost:8501")
    print(f"  3. 在 MQTT 标签页中测试命令下发和设备监控\n")
    
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
