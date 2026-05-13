# UDP Tool

用于测试当前工程的两类 UDP 通信：

1. `5568` AMBL 实时灯效帧
2. `5569` JSON 命令口

脚本位置：

- [tools/udp_tool/udp_tool.py](tools/udp_tool/udp_tool.py)

## 示例

发送 1 个红色像素到 `239.255.23.42:5568`：

```bash
python3 tools/udp_tool/udp_tool.py ambl --pixels 255,0,0,255
```

发送 3 个像素的 AMBL 帧：

```bash
python3 tools/udp_tool/udp_tool.py ambl --sequence 7 --pixels "255,0,0,255;0,255,0,255;0,0,255,255"
```

连续发送 100 帧，每 33ms 一帧：

```bash
python3 tools/udp_tool/udp_tool.py ambl --pixels 255,0,0,255 --count 100 --interval-ms 33
```

持续循环发送，直到手动停止：

```bash
python3 tools/udp_tool/udp_tool.py ambl --pixels "255,0,0,255;0,255,0,255" --repeat --interval-ms 16
```

发送 UDP JSON 命令到设备 `192.168.9.100:5569`：

```bash
python3 tools/udp_tool/udp_tool.py json --target 192.168.9.100 --payload '{"cmd":"list_timer"}'
```

从文件发送 JSON 命令：

```bash
python3 tools/udp_tool/udp_tool.py json --target 192.168.9.100 --payload-file payload.json
```

监听本地 UDP 端口：

```bash
python3 tools/udp_tool/udp_tool.py listen --port 5569 --text
```

## 说明

- `ambl` 命令会按工程协议构造 `AMBL` 帧头。
- `pixels` 参数使用 `RGBA` 顺序，每个像素 4 字节。
- `ambl` 默认单发 1 帧；可通过 `--count` 和 `--interval-ms` 做压力测试，也可通过 `--repeat` 持续发送。
- `json` 默认等待一帧 UDP 回包；若只发送不接收，可加 `--no-response`。