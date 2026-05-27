# 编译、烧录与监测指南

> **本文档适用于**：开发者、QA测试工程师、系统集成工程师  
> **最后更新**：2026-04-17  
> **状态**：📌 验证完成 (RTC 网络时间同步集成)

---

## 快速开始

### 前提条件

- **硬件**：ESP32-S3 开发板 + USB-UART 线缆
- **工具**：
  - ESP-IDF v5.4.1 或更新版本
  - xtensa-esp-elf 工具链
  - Python 3.7+
- **环境变量**：
  ```bash
  export IDF_PATH=/path/to/esp-idf
  export PATH=$IDF_PATH/tools:$PATH
  ```

### 一键编译 & 烧录 & 监测

```bash
cd /home/ats/standard_code/Aputure_IP_Project
idf.py flash monitor
```

**按 Ctrl+] 退出监测界面** | **按 Ctrl+T 然后 Ctrl+H 查看帮助菜单**

---

## 详细编译流程

### 1. 清理与重新编译

```bash
# 完全清理（删除 build/ 目录）
idf.py fullclean

# 重新编译
idf.py build
```

### 2. 指定编译目标

```bash
# 编译特定组件
idf.py build -B build main

# 看编译进展
idf.py build -VERBOSE
```

### 3. 常见编译错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `undefined reference to '_Z12app_rtc_initv'` | C/C++ 名字改编冲突 | 检查 `app_rtc.h` 是否有 `extern "C"` 保护 |
| `CMay be a linking failure` | 缺少依赖组件 | 检查 `main/CMakeLists.txt` 的 REQUIRES 字段 |
| `No rule to make target '_build'` | 编译路径错误 | 运行 `idf.py fullclean` 后重新 build |
| `mbedtls_ssl_handshake failed` | MQTT TLS 证书问题 | 见下文"MQTT 证书验证" |

---

## 烧录指南

### 烧录参数自动检测

```bash
idf.py flash
```

**ESP-IDF 会自动**：
- 检测串口设备（通常 `/dev/ttyACM0` 或 `/dev/ttyUSB0`）
- 识别芯片型号与 FLASH 容量
- 选择合适的烧录速率

### 手动指定串口

```bash
idf.py -p /dev/ttyACM0 flash
```

### 烧录验证

烧录完毕后日志应显示：
```
Wrote xx bytes to address 0x... in xxx ms
Hard resetting via RTS pin...
```

若出现 **port is busy** 错误：
```bash
# 找出占用的进程
lsof | grep ttyACM0

# 杀死占用
kill -9 <PID>

# 重试烧录
idf.py flash
```

---

## 监测与日志收集

### 实时监测

```bash
# 基础监测
idf.py monitor

# 带时间戳的监测
idf.py monitor --timestamps

# 指定波特率
idf.py monitor -b 115200
```

### 日志级别控制

在 `sdkconfig` 中配置：
```
CONFIG_LOG_DEFAULT_LEVEL_INFO=y    # 默认显示 INFO 及以上
```

或在代码中动态设置：
```c
esp_log_level_set("*", ESP_LOG_INFO);  // 所有标签
esp_log_level_set("mqtt-agent", ESP_LOG_DEBUG);  // 特定模块
```

### 日志重定向到文件

```bash
idf.py monitor | tee /tmp/device_$(date +%s).log
```

---

## 关键启动序列验证

### ✅ 预期启动日志

```
🟢 系统初始化 (389ms)
I (389) app_init: Compile time: Apr 17 2026 06:23:29
I (408) AputureIP: logger initialized
I (409) aputure-matter: booting Aputure IP with Matter integration

🟢 本地灯控初始化 (496ms)
I (496) local_db: 光效类型：1亮度：31478
I (529) dev_lamp: 1ms软件定时器初始化完成！
I (552) stack_monitor: stack snapshot begin: task_count=18

🟢 Matter 入口初始化 (1126ms)
I (1126) chip[DL]: CHIPoBLE advertising started
I (1131) chip[DL]: Starting ESP WiFi layer

🟢 WiFi 连接 (1222ms)
I (1222) wifi:connected with AP-IOT, aid = 6, channel 1
I (1232) chip[DL]: Posting ESPSystemEvent: Wifi Event with eventId : 4

🟢 IP 就绪 - 网络服务启动 (2260ms)
I (2260) ambient_wifi: got ip: 192.168.9.105
I (2264) chip[DL]: IP_EVENT_STA_GOT_IP

🔵 RTC 时区同步启动 (同上)
I (2248) aputure-matter: network time/timezone sync task started after IP ready
I (2247) TIMEZONE_SYNC: 创建时区同步管理器...
I (3248) TIMEZONE_SYNC: 已连接WiFi
I (3248) GEO_LOCATION: 查询地理位置，使用API: http://ip-api.com/json/...
I (4068) GEO_LOCATION: 地理位置查询成功: China, Guangdong, Shenzhen
I (4071) SNTP_TIME: 初始化SNTP时间服务...
I (4965) SNTP_TIME: 时间同步完成
I (5049) app_rtc: 当前时间: 2026-04-17 14:29:03

🟢 UDP 接收器启动 (同上)
I (2263) ambient_receiver: listening on 239.255.23.42:5568

🟢 MQTT 初始化 (同上)
I (2249) mqtt-agent: MQTT client_id=aputure-1cdbd4767084
I (2249) mqtt-agent: MQTT report topic=report/data
I (2251) mqtt-agent: MQTT agent started, broker=mqtts://broker.emqx.io:8883

🟢 Matter 服务发布 (2277ms)
I (2277) chip[DIS]: CHIP minimal mDNS started advertising.
I (2278) chip[DIS]: Advertise operational node 87D16BC3F5A7002D-00000000F100BD06
I (2279) chip[DIS]: mDNS service published: _matter._tcp

🟢 系统就绪 (2530ms)
I (2530) app-devicecallbacks: Server initialization complete
```

### ⚠️ 常见异常日志与应对

| 日志 | 含义 | 处理 |
|------|------|------|
| `E (2748) esp-tls-mbedtls: mbedtls_ssl_handshake returned -0x2700` | MQTT TLS 握手失败 | 检查 broker CA 证书、网络连接 |
| `W (560) stack_monitor: LOW STACK task=ipc0 free_min=456B (<512B)` | IPC 任务栈溢出风险 🔴 | 需要增加 IPC 栈大小（待优化） |
| `I (3594) app_rs485_master: 从机未连接` | RS485 从机离线 | 检查硬件连接、从机电源 |
| `E (3720) chip[DMG]: Fail to retrieve data, roll back ... err = 501` | Matter 属性读权限问题 | 正常处理，已回滚，无需关注 |
| `Guru Meditation: Coprocessor exception` | ISR 中执行浮点运算 | 已通过移到软件定时器回调修复 |

---

## 编译配置 (sdkconfig)

### 关键配置项

```ini
# 主要串口 (USB-UART 还是 USB Serial/JTAG)
CONFIG_ESP_CONSOLE_UART_TX_GPIO=17
CONFIG_ESP_CONSOLE_UART_RX_GPIO=18
CONFIG_ESP_CONSOLE_UART_NUM=1
CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y   # 使用 USB JTAG (推荐)

# FreeRTOS 时钟频率 (RTC 同步需要较高解析度)
CONFIG_FREERTOS_HZ=1000                 # 1ms 精度

# 蓝牙 (可选)
CONFIG_BT_ENABLED=y
CONFIG_BLUEDROID_ENABLED=y              # 或 CONFIG_NIMBLE_ENABLED=y

# 日志输出等级
CONFIG_LOG_DEFAULT_LEVEL_INFO=y

# 本地输出 (CPU1 灯控)
CONFIG_LOCAL_OUTPUT_ENABLE_BLUETOOTH_APP=n  # 蓝牙协议 (当前禁用)
```

### 重新配置

```bash
idf.py menuconfig
```

进入后依次导航：
- Component config → ESP32S3-Specific → UART/USB 配置
- Component config → FreeRTOS → Tick rate Hz
- Component config → Bluetooth → 蓝牙配置

修改后 **保存** → 自动重新编译

---

## MQTT 证书验证问题处理

### 问题表现

```
E (2749) esp-tls-mbedtls: Failed to verify peer certificate!
E (2752) mqtt_client: Error transport connect
```

### 解决步骤

1. **验证 Broker 连通性**
   ```bash
   # 测试 broker.emqx.io 是否可达
   ping broker.emqx.io
   timeout 5 openssl s_client -connect broker.emqx.io:8883 -showcerts
   ```

2. **检查嵌入式 CA 证书**
   ```bash
   # 查看当前嵌入证书
  xxd components/network/mqtt_agent/certs/emq_root_ca.pem | head -20
   ```

3. **临时禁用证书验证** (仅测试)
   ```c
  // 在 components/network/mqtt_agent/src/mqtt_agent.c 中
   esp_tls_cfg_t tls_cfg = {
       .crt_bundle_attach = esp_crt_bundle_attach,
       .skip_cert_common_name_check = true,  // ⚠️ 仅测试，生产禁用
   };
   ```

4. **使用环境变量覆盖证书**
   ```bash
   export MQTT_BROKER_CERT_PATH=/path/to/ca.pem
   idf.py flash monitor
   ```

---

## 长期稳定性测试

### 24 小时运行脚本

```bash
#!/bin/bash
START=$(date +%s)
DEVICE=/dev/ttyACM0
LOGFILE="/tmp/aputure_24h_$(date +%Y%m%d_%H%M%S).log"

echo "测试开始，日志保存到 $LOGFILE"
idf.py -p $DEVICE monitor --timestamps 2>&1 | while IFS= read -r line; do
    echo "$line" >> $LOGFILE
    
    # 检查崩溃关键字
    if echo "$line" | grep -E "Guru Meditation|panic|assert"; then
        echo "⛔ 检测到崩溃！" >&2
        break
    fi
done

END=$(date +%s)
echo "测试耗时: $((END - START)) 秒"
```

运行：
```bash
chmod +x run_24h_test.sh
./run_24h_test.sh
```

### 监测指标

- **堆内存**：监测 `Free heap` 是否持续下降（内存泄漏）
- **栈使用**：监测最小栈剩余是否接近警告阈值 512B
- **任务数**：监测任务数是否稳定（无泄漏的任务创建）
- **WiFi 重连**：检查 IP lost/got 是否频繁或卡住
- **日志频率**：是否有无限循环的错误日志

---

## 故障排查清单

```
□ 编译通过？
  └─ 若否：检查 CMakeLists.txt、include path、依赖
  
□ 烧录成功？
  └─ 若否：检查串口线、驱动程序、权限 (chmod 666)
  
□ 启动完成？
  └─ 若否：查看启动序列日志，locate 第一个异常
  
□ WiFi 连接？
  └─ 若否：检查 SSID/密码配置、信号强度、路由器
  
□ IP 获取？
  └─ 若否：检查 DHCP 配置、路由器 DHCP 池
  
□ RTC 同步？
  └─ 若否：检查网络、地理定位 API、SNTP 服务器
  
□ MQTT 连接？
  └─ 若否：检查 broker 地址、TLS 证书、网络延迟
  
□ Matter 发现？
  └─ 若否：检查 mDNS 打印日志、局域网配置
  
□ 灯具响应？
  └─ 若否：检查 IPC、本地输出链路、PWM 驱动
```

---

## 编译性能优化

### 加速编译

```bash
# 并行编译 (使用所有 CPU 核)
idf.py -j$(nproc) build

# 仅重新编译修改的文件
idf.py build
```

### 增量编译

```bash
# 编译后，若只改了 main.cpp
idf.py build main.cpp
```

---

## 版本控制与发布

### 版本号格式

编辑 `CMakeLists.txt` 的 `project_version` 字段：
```cmake
project(aputure_ip_project VERSION 1.0.0)
```

### 自动生成版本号

```bash
# 基于 git tag
git describe --tags --always > VERSION.txt
idf.py build
```

烧录后查看版本信息：
```
I (390) app_init: App version: ee0f4fe-dirty
I (390) app_init: Compile time: Apr 17 2026 06:23:29
```

---

## 相关链接

- [ESP-IDF 官方文档](https://docs.espressif.com/projects/esp-idf)
- [ESP32-S3 技术规格书](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_cn.pdf)
- [项目架构文档](../architecture/ARCHITECTURE.md)
- [快速参考手册](./QUICK_REFERENCE.md)
