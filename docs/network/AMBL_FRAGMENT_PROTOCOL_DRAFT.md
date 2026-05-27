# AMBL Fragment Protocol Draft

## Goal

现有 AMBL v1 为单个 UDP 数据报承载整帧：

- header 固定 24 字节
- payload 为 `channel_count * 4` 字节 RGBA

在 462 灯珠场景下：

- `462 * 4 = 1848` 字节 payload
- 总 UDP payload 为 `1848 + 24 = 1872` 字节

这已经超过常见以太网下 IPv4 UDP 的不分片安全范围 `1472` 字节，导致：

1. IP 分片
2. 组播分片包在 Wi-Fi 链路上丢失概率高
3. 接收端经常整帧收不到

目标是设计 AMBL v2 分包协议，让 462 灯珠可以稳定传输，同时保持对现有 v1 单包模式的兼容。

## Design Principles

1. 保持 `5568` 端口不变
2. 保持 `AMBL` magic 不变，使用 `version = 2` 区分新协议
3. 对于小帧仍允许沿用 v1 单包发送
4. 对于大帧按通道分片，而不是按裸字节分片，避免 RGBA 被截断
5. 接收端只做“尽快重组，超时即丢”，不引入 ACK / 重传，保持实时流语义
6. 优先最新帧，旧帧不完整时可直接淘汰

## Wire Format

### Common

- 传输: UDP 组播
- 目标: `239.255.23.42:5568`
- 字节序: 网络字节序
- 每个通道仍为 `RGBA` 4 字节

### AMBL v1

保留现状，不改。

### AMBL v2 Fragment Header

建议头部固定 36 字节：

```c
typedef struct __attribute__((packed)) {
    uint32_t magic;                   // 0x414D424C = 'AMBL'
    uint16_t version;                 // 2
    uint16_t header_size;             // 36
    uint32_t sequence;                // 帧序号，整帧所有分片共享同一个 sequence
    uint16_t total_channel_count;     // 整帧总通道数
    uint16_t fragment_channel_offset; // 当前分片起始通道偏移
    uint16_t fragment_channel_count;  // 当前分片通道数
    uint16_t fragment_index;          // 当前分片序号，从 0 开始
    uint16_t fragment_count;          // 整帧分片总数
    uint16_t flags;                   // 预留，当前置 0
    uint64_t timestamp_us;            // 整帧时间戳，所有分片相同
    uint32_t frame_crc32;             // 整帧 RGBA payload 的 CRC32
} ambl_v2_fragment_header_t;
```

分片 payload:

- 长度必须满足 `fragment_channel_count * 4`
- 数据内容为该分片对应范围内的 RGBA 连续数组

## Fragment Size

### Safe Payload Target

建议将单个 UDP payload 限制在 `1472` 字节以内，避免 IP 分片。

对于 v2：

- 头部 `36` 字节
- 可用于像素数据的安全空间为 `1472 - 36 = 1436` 字节
- 按 RGBA 对齐，单片最大通道数为：

```text
floor(1436 / 4) = 359 channels
```

### 462 LEDs Example

462 灯珠需要：

```text
462 * 4 = 1848 bytes payload
```

可拆为 2 片：

1. fragment 0
   - `fragment_channel_offset = 0`
   - `fragment_channel_count = 359`
   - payload = `1436` bytes

2. fragment 1
   - `fragment_channel_offset = 359`
   - `fragment_channel_count = 103`
   - payload = `412` bytes

这样两片都低于安全 MTU，不触发 IP 分片。

## Sender Rules

### v1 / v2 Selection

发送端建议按如下规则自动选择：

1. 如果 `24 + channel_count * 4 <= 1472`
   - 发送 v1 单包
2. 否则
   - 发送 v2 分片

### v2 Fragment Emission

发送端对一帧像素数据执行：

1. 计算整帧 `sequence`
2. 计算整帧 `timestamp_us`
3. 计算整帧 `frame_crc32`
4. 按 `359` 通道一片切分
5. 对每个分片填入相同的：
   - `sequence`
   - `timestamp_us`
   - `total_channel_count`
   - `fragment_count`
   - `frame_crc32`
6. 对每片分别填入：
   - `fragment_index`
   - `fragment_channel_offset`
   - `fragment_channel_count`

### Ordering

建议按 `fragment_index` 顺序发送，但接收端必须支持乱序到达。

### No Retransmission

AMBL 是实时流，不建议为组播增加 ACK / NACK / 重传。

策略应为：

1. 缺片就丢整帧
2. 依赖下一帧覆盖

## Receiver Rules

### Compatibility

接收端在同一个 `5568` 端口同时支持：

1. `version == 1` 的现有单包协议
2. `version == 2` 的分片协议

### Reassembly State

建议维护一个小型重组表，按 `(sequence, timestamp_us)` 标识一帧。

每个重组条目建议包含：

```c
typedef struct {
    bool in_use;
    uint32_t sequence;
    uint64_t timestamp_us;
    uint16_t total_channel_count;
    uint16_t fragment_count;
    uint16_t received_fragments;
    uint32_t frame_crc32;
    uint32_t received_bitmap[8];     // 足够覆盖最多 256 片，当前远超需求
    uint8_t rgba[CONFIG_AMBIENT_MAX_CHANNELS * 4];
    int64_t first_seen_us;
    int64_t last_seen_us;
} ambl_reassembly_slot_t;
```

实际项目里 462 灯珠只需 2 片，因此 2 到 4 个 slot 已足够。

### Validation

接收端对每个 v2 分片应校验：

1. `magic == 'AMBL'`
2. `version == 2`
3. `header_size == 36`
4. `fragment_channel_count > 0`
5. `fragment_channel_offset + fragment_channel_count <= total_channel_count`
6. `total_channel_count <= CONFIG_AMBIENT_MAX_CHANNELS`
7. payload 长度等于 `fragment_channel_count * 4`
8. `fragment_index < fragment_count`

### Reassembly Policy

收到有效分片后：

1. 按 `fragment_channel_offset * 4` 把 payload 拷入整帧缓冲区
2. 标记该 `fragment_index` 已收到
3. 更新 `last_seen_us`
4. 如果所有分片已到齐：
   - 计算整帧 RGBA 的 CRC32
   - 与 `frame_crc32` 比较
   - 一致则提交到 `ambient_output_submit_frame`
   - 不一致则丢弃

### Freshness Policy

为了保持实时性，建议：

1. 每个重组 slot 超时 `20~30ms` 后自动丢弃
2. 如果收到更大的 `sequence`，且旧帧仍未拼完整，可以直接淘汰旧帧
3. 只提交“最新完成帧”给输出任务

这意味着：

1. 不追求可靠传输
2. 追求连续刷新时的低延迟与稳定性

## Why CRC32

虽然 UDP 已有校验和，但分片重组完成后增加一层整帧 CRC32 仍有价值：

1. 能发现拼接错误或状态污染
2. 可避免不同 sequence 的残片错误混合
3. 便于调试和统计坏帧率

## Backward Compatibility Strategy

### Receiver Side

设备端升级后：

1. 保持支持 v1
2. 新增支持 v2

这样现有工具和旧发送端不需要立即改。

### Sender Side

上位机工具升级后：

1. 小帧继续发 v1
2. 大帧自动发 v2

建议在工具中加入显式开关：

- `--ambl-version auto|1|2`

默认 `auto`。

## Recommended Limits

建议把这些值做成明确常量：

```text
AMBL_SAFE_UDP_PAYLOAD = 1472
AMBL_V1_HEADER_SIZE   = 24
AMBL_V2_HEADER_SIZE   = 36
AMBL_MAX_CHANNELS     = 500
AMBL_REASSEMBLY_SLOTS = 4
AMBL_REASSEMBLY_TIMEOUT_MS = 30
```

## Example v2 Frame Sequence

针对 462 灯珠、sequence=100：

### Fragment 0

- sequence = 100
- total_channel_count = 462
- fragment_index = 0
- fragment_count = 2
- fragment_channel_offset = 0
- fragment_channel_count = 359

### Fragment 1

- sequence = 100
- total_channel_count = 462
- fragment_index = 1
- fragment_count = 2
- fragment_channel_offset = 359
- fragment_channel_count = 103

接收端只有在两片都收到且 CRC32 校验通过后，才把整帧 462 通道提交给输出层。

## Migration Plan

建议分三步落地：

1. 设备端先增加 v2 接收和重组，保留 v1
2. Python / Kotlin / 上位机工具增加 `auto` 分片发送
3. 完成联调后，再决定是否把大于 `362` 通道的 v1 发送直接禁止

## Non-Goals

本草案暂不包含：

1. 组播 ACK / NACK
2. 发送端重传
3. FEC 前向纠错
4. 压缩编码

这些都可以作为后续增强，但不是 462 灯珠稳定传输的第一步。