# ESP32S3 智能灯具 - 开发检查清单与测试计划

> 状态说明：本文保留了 2026-04-21 的阶段性清单回填结果与测试模板。文中带有 `✓` 的子项大多表示“当时的目标或已做过一次验证”，不应自动视为 2026-05-19 仍然成立的现状结论。
>
> 当前使用方式建议：
> - 把本文当作回归测试模板和历史验证记录
> - 新一轮验证时重新逐项打勾，不要直接继承旧勾选结果
> - 若需要看当前结构与路径，请配合 `docs/development/BUILD.md`、`docs/development/QUICK_REFERENCE.md`、`docs/architecture/PROJECT_STRUCTURE.md`

## 🎉 最新成果 (2026-04-21 更新)

### ✅ Phase 3/4 进度检测完成 + IP 定期检查落地 + 配置化完善

**2026-04-21 改动概要（最新）：**
```
✅ Matter API 调用切换到 ScheduleWork — 修复长按配网触发的 CHIP lock assert
✅ 工厂复位补充 WiFi 清理 — disconnect/stop/restore 后再 ScheduleFactoryReset
✅ 温度采集链路启用 — app_power_adc_temp_handle() 实际采样并写入系统状态
✅ 过温联动降功率生效 — over_temp=true 时下调 lamp power_limit，恢复后自动回升
✅ 热保护参数 Kconfig 化 — 阈值/恢复阈值/降功率/正常功率 共 4 项可调
✅ Phase 3/4 开发进度检测完成 — 清单状态按代码现状回填（网络/BLE/MQTT/UDP/Matter）
✅ IP 定期有效性检查落地 — ambient_wifi 新增后台轮询 + Kconfig 参数化
✅ reconfigure + build 通过 ✓ 固件 0x1CD070 (1,888,368B), 40% 剩余
```

**项目评分 (2026-04-21)：**
```
功能完整性:    89%  (Phase 3/4 清单与代码状态对齐)
代码质量:      84%  (网络观测参数进入 Kconfig，可维护性提升)
运行稳定性:    74%  (新增 IP 定期检查，连接状态自愈能力增强)
生产就绪度:    75%  (核心链路更清晰，仍需 MQTT TLS 与长期稳定性验证)
预计生产就绪:  2026-05-15（历史预测，现已过期）
```

**未解决遗留问题：**
```
🟡 MQTT TLS 证书问题      (握手 -0x2700)  → 待排查
🟡 RS485 从机重连机制     (无主动重连)     → 待实现
🟡 BLE 升级界面入口控制   (升级中需禁止进入) → app_bluetooth.c TODO
🟢 长期稳定性验证        (需 24h+ 测试)  → 待执行
```

---

## 📋 RTC 功能验证清单

> 新增于 2026-04-17，用于 RTC/SNTP 功能验收

```
□ 地理定位成功
    日志: "GEO_LOCATION: 地理位置查询成功: China, Guangdong, Shenzhen"
    验证: 检查地理位置是否与实际地点相符
  
□ 时区自动识别
    日志: "TIMEZONE_SYNC: 时区设置为 Asia/Shanghai"
    验证: 与您的地理位置时区一致
  
□ SNTP 时间同步
    日志: "SNTP_TIME: 时间同步完成: 2026-04-17 14:29:03"
    验证: 时间与北京时间误差 <1 分钟
  
□ 系统时间精确
    代码验证:
        time_t now = time(NULL);
        struct tm* tm = localtime(&now);
        printf("%d-%02d-%02d %02d:%02d:%02d", ...)
    验证: 输出为 UTC+8 格式（如在中国）
  
□ 时间持久化
    验证: 重启设备后，系统时间从上次关闭时间继续计数
    精度: ±10 分钟内为正常（由 NVS 持久化特性决定）
  
□ IP-Ready-Gate 启动时序
    顺序: IP 就绪 → RTC 初始化 → MQTT/UDP 启动
    验证: 查看日志中是否按此顺序出现
```

---

## 状态同步（2026-04）

**说明**：本章节用于同步"文档目标"与"代码现实"，避免状态失真。

补充说明（2026-05-19）：以上“代码现实”口径仍是 2026-04-21 的审查结果；本轮已完成的是文档结构与路径校正，不等于重新完成了一遍所有功能和性能回归。

- 构建状态：`idf.py reconfigure && idf.py build` 已通过（2026-04-21 验证，固件 0x1CD070）
- **唯一生效入口**：`main/main.cpp::app_main()`
- 状态标记：`[x]` 已完成，`[~]` 部分/占位完成，`[ ]` 未完成
- 新增配置汇总：`CONFIG_AMBIENT_IP_CHECK_INTERVAL_MS=5000`（Wi-Fi IP 定期有效性检查间隔）
- **最后更新**：2026-04-21

## 核心改进 (2026-04)

- [x] **工程结构重构** ⭐ (2026-04-20)
        - [x] components/ 拆分为 8 个功能子目录
        - [x] CMakeLists.txt EXTRA_COMPONENT_DIRS 更新
    - [x] 3 个本地能力文件接入主链路 (app_power, app_use_btn, app_debug)
    - [x] 清理未使用服务编排代码（main/boot 下 system_bootstrap/service_registry 等）
        - [x] 编译验证通过

- [x] **Kconfig 配置统一** ⭐ (2026-04-20)
        - [x] 全部项目配置归入 "(Top) → Project Configuration" 下 4 个子菜单
        - [x] 删除 mqtt_agent 组件级 Kconfig
        - [x] project_config.h 改用 sdkconfig.h + #ifndef 兜底
        - [x] app_debug.c UART 引脚使用 CONFIG_ Kconfig 宏
        - [x] sdkconfig.defaults 新增 Product Profile / MQTT Agent 默认值

- [x] **RTC/SNTP 时间同步** (2026-04-17)
        - [x] 地理定位 API 集成（ip-api.com）
        - [x] 自动时区识别（CST-8 验证正确）
        - [x] SNTP 多服务器支持
        - [x] 系统时间自动校准（精度 ±100ms）
        - [x] 时间数据持久化到 NVS
        - [x] IP 就绪后自动启动

- [x] **温度保护闭环与参数化** ⭐ (2026-04-21)
    - [x] 温度采集链路启用（芯片温度传感器，周期写入 board_temp / led_temp）
    - [x] over_temp 滞回判定（过温阈值与恢复阈值分离）
    - [x] 过温联动功率限制（降功率与恢复功率自动切换）
    - [x] Kconfig 新增 4 项热保护参数并写入 sdkconfig.defaults
    - [x] 编译验证通过（含 reconfigure）

- [x] **网络管理观测增强** ⭐ (2026-04-21)
    - [x] Phase 3/4 云连接协议进度检测与清单回填
    - [x] ambient_wifi 增加 netif IP 定期有效性检查任务
    - [x] 新增 `CONFIG_AMBIENT_IP_CHECK_INTERVAL_MS`（默认 5000ms）
    - [x] QUICK_REFERENCE / PROJECT_SUMMARY / DEVELOPMENT_CHECKLIST 文档口径统一

## 一、核心模块优先级与开发顺序

### Phase 1: 基础架构 (第1-2周)

- [x] **状态管理器 (state_manager)**
    - [x] 状态结构体定义（含 matter_level / color_hue / sat / x / y / color_mode）
    - [x] 线程安全的get/set方法
    - [x] NVS持久化（STATE_STORE_VERSION=3）
    - [x] 状态变化回调机制（state_manager_register_callback，最多4路监听）
    - [x] 版本号自动递增
    - [x] 时间戳管理
  
- [x] **IPC通信层 (ipc_manager)**
    - [x] FreeRTOS队列初始化
    - [x] 跨CPU消息发送
    - [x] 消息序列化/反序列化
    - [~] 优先级队列支持
    - [ ] 队列监控与统计
  
- [x] **协议分发器 (protocol_dispatcher)**
    - [~] 协议注册/注销框架
    - [x] 状态同步分发函数
    - [~] 环路检测机制
    - [x] 协议在线状态管理

**关键指标**：
✓ 两核可以正常通信
✓ 状态变化可自动同步
✓ 不会产生环路

---

### Phase 2: CPU1 本地业务 (第2-3周)

- [~] **输入系统 (input_system)**
  - [x] GPIO按键驱动 (FlexibleButton + GPIO37)
  - [x] 按键去抖及长按检测 (单击开关/3s配网/6s复位)
  - [ ] 红外遥控解码(可选)
  - [ ] 传感器接口(温度、光照等)
  - [ ] 事件队列管理
  
- [x] **输出系统 (output_system)**（CPU1 任务链路已通；下列子项为占位实现，待接硬件驱动）
  - [~] PWM亮度控制（占位：打印 level=%u/254 -> brightness=%u%%，待接 LEDC 驱动）
  - [~] 色温调节（占位：color_temp 已传入，待接 CCT 混光算法）
  - [~] LED驱动（占位：power/brightness/mode 已打印）
  - [~] 继电器控制（占位：power 已打印，待接 GPIO）
  - [x] CPU1 独立任务（xTaskCreatePinnedToCore core=1，队列长度1，xQueueOverwrite 无积压）
  - [x] local_output 组件桥接（state_manager 回调 → output_system_apply_state）
  
- [~] **定时/循环任务 (scheduler)**
  - [~] 本地RTC时钟管理（app_rtc 线程已运行并周期写入 sys_status，闹钟能力未接入业务调度）
  - [ ] CRON表达式解析(定时任务)
    - [x] 倒计时任务（已新增 app_countdown 模块，支持 MQTT 下发、NVS 持久化、单次/每日/每周执行）
  - [~] 循环扫描任务（已存在按键/功率/DB 周期循环，但未统一为 scheduler 框架）
  
- [~] **业务逻辑层 (device_logic)**
    - [~] 灯开关状态机（已实现开/关与状态持久化流转，显式多态状态机待完善）
    - [x] 亮度渐变算法（dev_lamp 1ms 渐变回调 + fade_time 生效）
    - [x] 色温转换（color_calc_cct 主链路已接入）
    - [x] 动画引擎框架（light_effect / SidusProFX / pixel_fx 已接入）

**关键指标**：
✓ 按键可控制灯光
✓ 定时任务准时执行
✓ 动画流畅无卡顿

---

### Phase 3: CPU0 网络基础 (第3-4周)

- [~] **网络管理器 (network_manager)**
    - [~] WiFi扫描与连接（由 Matter ConnectivityManager 接管，应用层保留状态观测）
    - [x] IP获取验证（已接入 IP_EVENT_STA_GOT_IP/LOST_IP 与日志）
    - [x] IP定期有效性检查（ambient_wifi 后台轮询 netif IP 并校正连接状态）
    - [x] 网络状态转移（IP 丢失时 UDP offline，恢复后自动拉起网络服务）
    - [~] 心跳监测机制（MQTT keepalive 已有，统一网络心跳未独立实现）
  
- [~] **BLE协议 (ble_task)**
    - [~] BLE Advertise配置（Matter CHIPoBLE 可用；本地 BLE 协议默认关闭）
    - [~] GATT Service定义（Matter GATT 可用；本地 Sidus BLE 待启用联调）
    - [~] Characteristic实现（本地 Sidus BLE 待启用联调）
    - [~] 命令解析（app_bluetooth 命令分发已在代码中，默认未编入主链路）

**Phase 3 检测结论（2026-04-21）**：完成度约 **65%**，WiFi/IP 主链路已可运行，BLE 本地控制链路仍处于“代码就绪、默认未启用、待联调验证”状态。
  
**关键指标**：
✓ 设备可被BLE扫描到
✓ 手机可通过BLE连接
✓ BLE可接收控制命令

---

### Phase 4: 云连接协议 (第4-6周)

- [~] **MQTT协议 (mqtt_task)**
    - [~] 连接代理服务器（客户端启动与连接流程已接入，TLS 证书握手仍待修复）
    - [x] 主题订阅/发布（report/device/group/all 主题已接入）
    - [x] 消息QoS管理（发布与订阅使用 QoS1）
    - [ ] 遗愿消息(LWT)
    - [x] 自动重连机制（ESP-MQTT auto reconnect 已启用）
  
- [~] **UDP协议 (udp_task)**
    - [x] 端口绑定和监听（组播 socket + 收包任务已运行）
    - [ ] 广播消息发送
    - [x] 远程命令解析（ambient_parse_frame + 输出链路接入）
    - [ ] 状态响应
  
- [~] **Matter协议 (matter_task)**
  - [x] Matter Stack初始化（connectedhomeip v1.5.0.1 接入构建链路）
  - [x] Fabric加入/创建（基础流程已跑通）
  - [x] OnOff Cluster 回调（UpdateOnOff → state_manager）
  - [x] Level Control 回调（UpdateBrightness，含 matter_level raw 值记录）
  - [x] Color Control 回调（Hue / Saturation / X / Y / ColorMode / ColorTemp 全属性）
  - [x] 事件主动上报（state_manager 回调 → ScheduleWork → Clusters::Set + MatterReportingAttributeChangeCallback）

**Phase 4 检测结论（2026-04-21）**：完成度约 **73%**，Matter 闭环已完成；MQTT 主链路可运行但受 TLS 握手与 LWT 缺项影响；UDP 接收链路已完成，发送与状态响应仍待实现。

**关键指标**：
✓ 云平台可接收设备状态
✓ 云平台可控制设备
✓ 多协议数据一致性
✓ 无冗余和环路

---

## 二、功能测试清单

### 基本功能测试

#### 本地控制
```
[ ] 测试1.1: 按键开/关灯
    - 按一次打开 ✓
    - 再按一次关闭 ✓
    - 长按进入调光模式 ✓
    
[ ] 测试1.2: 亮度调节
    - 滑块调节亮度0-100% ✓
    - 亮度变化流畅无跳跃 ✓
    - 保存后重启仍有效 ✓
    
[ ] 测试1.3: 色温调节
    - 色温范围2700K-6500K ✓
    - 调节流畅 ✓
    - 实时反馈 ✓
```

#### 定时任务
```
[ ] 测试2.1: 每日定时开灯
    - 设置早晨6:00开灯 ✓
    - 设置多个时间点 ✓
    - 时间到时自动执行 ✓
    - 可个别关闭某个定时 ✓
    
[ ] 测试2.2: 倒计时关灯
    - 设置30分钟后关灯 ✓
    - 显示剩余时间 ✓
    - 可随时取消 ✓
```

#### 动画效果
```
[ ] 测试3.1: 呼吸灯
    - 启动后循环变亮变暗 ✓
    - 频率可调 ✓
    - 停止后灯保持当前亮度 ✓
    
[ ] 测试3.2: 彩虹循环
    - 颜色循环变化流畅 ✓
    - 可设置速度 ✓
    - 与亮度调节兼容 ✓
```

### 网络功能测试

#### WiFi连接
```
[ ] 测试4.1: 初次配网
    - WiFi SScan成功 ✓
    - 用户选择并输入密码 ✓
    - 成功连接到路由器 ✓
    - 获取IP地址 ✓
    
[ ] 测试4.2: 断线重连
    - WiFi正常连接 ✓
    - 关闭路由器 ✓
    - 设备进入BLE-Only模式 ✓
    - 打开路由器，自动重连 ✓
    - 恢复网络后所有协议启动 ✓
    
[ ] 测试4.3: WiFi信号弱
    - WiFi信号从强变弱 ✓
    - 信号强度显示正确 ✓
    - RSSI更新实时 ✓
    - 不会频繁断线 ✓
```

#### MQTT协议
```
[ ] 测试5.1: MQTT连接
    - 成功连接到Broker ✓
    - 收到连接确认 ✓
    - 心跳正常(-60秒心跳间隔) ✓
    
[ ] 测试5.2: MQTT发布状态
    - 本地灯亮度变化 → MQTT发布 ✓
    - 发布主题正确 ✓
    - JSON格式正确 ✓
    - 云平台收到数据 ✓
    
[ ] 测试5.3: MQTT接收控制
    - 云平台发送开灯命令 ✓
    - 灯立即打开 ✓
    - 云平台接收反馈 ✓
    - 防止指令环路 ✓
    
[ ] 测试5.4: MQTT离线处理
    - 断开网络 → MQTT断开 ✓
    - 恢复网络 → MQTT自动重连 ✓
    - 离线期间的本地变化，上线后同步 ✓
```

#### BLE协议
```
[ ] 测试6.1: BLE广播
    - 设备可被BLE扫描发现 ✓
    - 广播包中包含正确的UUID ✓
    - 广播间隔在可接受范围内 ✓
    
[ ] 测试6.2: BLE连接
    - 手机可连接到设备 ✓
    - 连接后可访问Service ✓
    - 一次仅一个设备连接 ✓
    
[ ] 测试6.3: BLE控制
    - 手机向设备发送开灯命令 ✓
    - 灯立即响应 ✓
    - 灯状态实时推送到手机 ✓
    
[ ] 测试6.4: 网络状态下的BLE
    - WiFi在线，BLE仍可使用 ✓
    - WiFi离线，BLE保持可用 ✓
    - BLE和其他协议不冲突 ✓
```

#### UDP协议
```
[ ] 测试7.1: UDP广播
    - 本地灯亮度变化 → UDP广播 ✓
    - 同局域网设备可接收 ✓
    - 无需云端中转，极速响应 ✓
    
[ ] 测试7.2: UDP控制
    - 同局域网APP发送UDP命令 ✓
    - 灯立即响应 ✓
    - 反馈发送回APP ✓
```

#### Matter协议
```
[ ] 测试8.1: Fabric加入
    - 首次配网时创建Fabric ✓
    - 加入现有Fabric ✓
    - 设备集成到HomeKit/Google Home ✓
    
[ ] 测试8.2: Matter控制
    - 通过HomeKit打开/关闭灯 ✓
    - 通过HomeKit调整亮度 ✓
    - 通过Google Home语音控制 ✓
    - 状态同步及时 ✓
```

#### 温度与热保护
```
[ ] 测试9.1: 热保护参数合法性
    - OVER_TEMP > RECOVER_TEMP ✓
    - 建议滞回 >= 5°C (避免抖动) ✓
    - DERATE_POWER_LIMIT < NORMAL_POWER_LIMIT ✓
    - 修改参数后执行 idf.py reconfigure && idf.py build ✓

[ ] 测试9.2: 过温触发降功率
    操作: 提升温度至 over_temp 阈值以上
    预期: over_temp=true ✓
           lamp power_limit 自动下调至 DERATE_POWER_LIMIT ✓
    验证: 日志包含 over_temp / power_limit 变化 ✓

[ ] 测试9.3: 恢复阈值回升
    操作: 降温至 recover_temp 阈值以下
    预期: over_temp=false ✓
           lamp power_limit 恢复到 NORMAL_POWER_LIMIT ✓
    验证: 日志出现恢复事件且不抖动 ✓

[ ] 测试9.4: 长稳态回归
    操作: 固定负载运行 20-30 分钟
    预期: 不出现频繁进出过温(阈值抖动) ✓
           功率限制与温度趋势匹配 ✓
```

### 多协议同步测试

```
[ ] 测试10.1: 本地 → 云平台同步
    操作: 按下按键打开灯
    预期: MQTT/Matter/UDP/BLE都收到更新 ✓
    验证: 云平台/App显示灯已开 ✓

[ ] 测试10.2: 云平台 → 本地同步
    操作: MQTT发送亮度命令(80%)
    预期: 灯立即变为80% ✓
    验证: Matter/UDP/BLE也显示80% ✓
    
[ ] 测试10.3: 多协议同时下发
    操作: 同时从MQTT、Matter、UDP三个渠道下发不同亮度
    预期: 最后一个赢(基于时间戳) ✓
    验证: 无冲突，无环路 ✓
    
[ ] 测试10.4: 防环路测试
    操作: A下发→B同步→C同步→A再发
    预期: 不会无限循环 ✓
    验证: 带版本号和时间戳防护 ✓
```

### 网络故障恢复测试

```
[ ] 测试11.1: WiFi无法连接
    操作: 设置错误的WiFi密码
    预期: 5次尝试后进入BLE-Only模式 ✓
    验证: BLE仍可本地控制 ✓
           用户可重新配网 ✓
    
[ ] 测试11.2: MQTT服务故障
    操作: MQTT Broker下线
    预期: MQTT标记离线 ✓
           其他协议继续工作 ✓
           自动定期重连 ✓
    
[ ] 测试11.3: 全网故障
    操作: 同时关闭WiFi和所有网络协议
    预期: 立即进入BLE-Only模式 ✓
           本地定时任务继续 ✓
           用户可BLE控制 ✓
    
[ ] 测试11.4: 恢复顺序
    操作: 先恢复WiFi，再恢复Broker
    预期: WiFi连接成功 ✓
           逐个协议上线 ✓
           完全恢复无延迟 ✓
           离线期间的变化已同步 ✓
```

### 性能与稳定性测试

```
[ ] 测试12.1: 内存泄漏
    操作: 运行72小时
    预期: 内存占用稳定 ✓
           无异常重启 ✓
    
[ ] 测试12.2: 响应时间
    本地按键 → LED亮起: < 50ms ✓
    MQTT下发 → LED响应: < 200ms ✓
    UDP下发 → LED响应: < 100ms ✓
    Matter下发 → LED响应: < 150ms ✓
    
[ ] 测试12.3: 并发控制
    操作: 同时从多个源接收控制命令
    预期: 无死锁 ✓
           无丢包 ✓
           状态一致 ✓
    
[ ] 测试12.4: 极限网络条件
    操作: WiFi信号-80dBm、频繁断线
    预期: 仍能正常通信 ✓
           自动降速自适应 ✓
```

## 三、发布清单

### 代码质量检查
- [ ] 所有函数都有错误处理
- [ ] 关键变量受互斥锁保护
- [ ] 无全局变量泄露
- [ ] 内存分配都有对应释放
- [ ] 日志级别合理(INFO/WARN/ERROR)
- [ ] 代码注释完整

### 文档完整性
- [ ] API文档完成
- [ ] MQTT主题文档完成
- [ ] Matter Cluster文档完成
- [ ] BLE Service/Characteristic文档完成
- [ ] 故障排查指南完成
- [ ] 开发者快速开始指南完成

### 安全性检查
- [ ] OTA升级支持
- [ ] 固件签名验证
- [ ] WiFi密码加密存储
- [ ] MQTT证书支持
- [ ] BLE绑定机制(可选)

### 打包与发布
- [ ] 编译出稳定固件版本
- [ ] 刷写工具与驱动
- [ ] ROM镜像备份
- [ ] 版本号记录(v1.0.0)
- [ ] CHANGELOG更新
- [ ] README中发布说明

---

## 四、CI/CD建议

### 构建流程
```bash
# 1. 拉取代码
git clone ...

# 2. 编译固件
idf.py build

# 3. 运行单元测试
pytest tests/

# 4. 生成报告
gcov report
```

### 自动化测试
```python
# pytest.ini - 自动化测试框架

# test_mqtt.py - MQTT协议测试
def test_mqtt_connect():
    # 验证MQTT连接
    pass

def test_mqtt_publish_state():
    # 验证状态发布
    pass

# test_state_sync.py - 状态同步测试
def test_state_version_increment():
    # 版本号递增
    pass

def test_no_infinite_loop():
    # 防环路
    pass
```

---

## 五、快速故障排查

| 问题 | 症状 | 检查项 |
|------|------|--------|
| BLE无法扫描到 | 手机扫描看不到设备 | ✓ BLE是否初始化<br/>✓ 广播是否启用<br/>✓ UUID是否匹配 |
| MQTT无法连接 | 日志显示"Connection refused" | ✓ Broker地址/端口<br/>✓ 网络是否在线<br/>✓ 防火墙设置 |
| 灯不响应 | 发送命令但无反应 | ✓ IPC队列是否堵塞<br/>✓ 状态管理器是否工作<br/>✓ GPIO引脚配置 |
| 频繁断网 | WiFi不断连接/断开 | ✓ WiFi信号强度<br/>✓ 路由器兼容性<br/>✓ WiFi重连策略 |
| 内存溢出 | 运行一段时间后崩溃 | ✓ 堆内存使用情况<br/>✓ 是否有内存泄漏<br/>✓ 栈溢出检查 |
| 数据重复 | 同一命令执行多次 | ✓ 版本号机制<br/>✓ 去重缓存<br/>✓ 环路检测 |

