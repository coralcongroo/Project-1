#!/usr/bin/env python3
"""
快速验证脚本 — 检查系统环境是否可以运行 MQTT Server & Monitor
"""
import subprocess
import sys
from pathlib import Path

def check(description: str, condition: bool) -> bool:
    symbol = "✓" if condition else "✗"
    status = "OK" if condition else "FAIL"
    print(f"  {symbol} {description:.<50} {status}")
    return condition

def run_check(cmd: str) -> bool:
    try:
        subprocess.run(cmd.split(), capture_output=True, timeout=2, check=True)
        return True
    except:
        return False

print("\n" + "="*70)
print("MQTT Server & Monitor 环境检查")
print("="*70 + "\n")

all_ok = True

# Python 版本
print("✓ Python 版本检查")
py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
all_ok &= check(f"Python >= 3.10", sys.version_info >= (3, 10))

# 系统命令
print("\n✓ 系统命令检查")
all_ok &= check("mosquitto", run_check("which mosquitto"))
all_ok &= check("pip", run_check("which pip"))

# Python 包
print("\n✓ Python 包检查")
for pkg in ["streamlit", "paho"]:
    try:
        __import__(pkg)
        check(f"package '{pkg}'", True)
    except ImportError:
        all_ok &= check(f"package '{pkg}'", False)

# 文件结构
print("\n✓ 文件结构检查")
project_dir = Path(__file__).parent.resolve()
files_to_check = [
    ("mqtt_server.py", "MQTT Server 管理器"),
    ("mqtt_monitor.py", "MQTT 监控客户端"),
    ("ui_app.py", "Streamlit UI"),
    ("debug_setup.py", "自动调试脚本"),
    ("requirements.txt", "Python 依赖清单"),
]

for filename, description in files_to_check:
    exists = (project_dir / filename).exists()
    all_ok &= check(f"{description:.<40} ({filename})", exists)

# 工作目录
print("\n✓ 工作目录检查")
workspace = project_dir / ".mqtt_server"
workspace_ok = workspace.exists()
if not workspace_ok:
    workspace.mkdir(parents=True, exist_ok=True)
check(".mqtt_server/ 目录", True)

# 最终结果
print("\n" + "="*70)
if all_ok:
    print("✓ 环境检查通过！可以开始使用")
    print("\n  快速开始:")
    print("    python debug_setup.py    # 一键自动调试")
    print("    make ui                  # 启动 Streamlit UI")
    print("    make help                # 查看所有命令")
else:
    print("✗ 环境检查失败，请安装缺少的依赖")
    print("\n  解决方案:")
    print("    pip install -r requirements.txt")
    print("    sudo apt install mosquitto")

print("="*70 + "\n")

sys.exit(0 if all_ok else 1)
