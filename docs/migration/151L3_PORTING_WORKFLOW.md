# 151_l3 后续更新移植流程

更新时间: 2026-05-19

## 目的

这份文档用于规范 `~/git-code/151_l3` 后续更新同步到当前工程时的处理流程，避免出现以下常见问题:

- 只按同名文件覆盖，忽略当前工程真实活跃路径
- 把当前工程已经增强或重构的部分误判为“还没迁”
- 把 framework 层回退成 151_l3 的单文件组织方式
- 做了代码移植但没有同步迁移表、对应表和检查清单

本流程同时适用于:

- 人工对照迁移
- 使用 `Aputure 151L3 Porting` agent 进行半自动分析与落地

## 适用范围

适用于所有以 `~/git-code/151_l3` 为上游源头、需要判断是否同步到当前工程的任务，尤其包括:

- 灯控路径更新
- RS485 主从逻辑更新
- PWM / GPIO / `Factory_RGBWW` 相关更新
- 本地输出链路更新
- 点光源固件与升级链更新
- 与 `151_l3` 对应关系文档的持续维护

## 基本原则

### 1. 先找活跃路径，再谈移植

当前工程不是 `151_l3` 的简单平移。

必须先确认当前工程里的活跃落点，再决定如何移植，不允许直接按 legacy 路径覆盖。

优先关注:

- `main/main.cpp`
- `components/app/local_output/`
- `main/app/app_light.c`
- `main/app/app_rs485_master.c`
- `main/light/*`
- `main/DeviceCallbacks.cpp`
- `components/framework/*`

### 2. 先分类，再动代码

每个 `151_l3` 更新都应先分到下面四类之一:

- 已对齐: 当前工程已有等价行为
- 已增强: 当前工程已有同类能力，而且实现比 legacy 更完整
- 未迁移: 当前工程确实缺少该行为
- 不建议直接迁: 当前工程已有更高层替代，直接搬运会破坏现有结构

### 3. 优先保留当前工程结构

当前工程已经形成以下高层骨架，默认不回退:

- `components/framework/state_manager/`
- `components/framework/ipc_manager/`
- `components/framework/protocol_dispatcher/`
- `components/app/local_output/`
- `main/light/light_control_bus.c`
- `main/light/light_control_facade.c`
- `main/DeviceCallbacks.cpp`

如果 `151_l3` 的更新与这些层冲突，优先迁移“行为”，不要回退“结构”。

## 标准处理步骤

### 步骤 1: 明确上游更新范围

至少固定以下一项:

- 具体文件路径
- 具体 commit
- 具体功能点
- 具体行为差异

如果输入过于笼统，例如“151_l3 更新了，帮我同步”，应先收窄范围。

### 步骤 2: 找当前工程的真实落点

不要先找同名文件，要先找“当前行为在哪条链上真正生效”。

优先判断:

- 这个行为是否进入当前主构建
- 它是在 `local_output`、`DeviceCallbacks`、`state_manager`、`app_rs485_master`、`app_light` 还是别的桥接层生效
- 当前工程是否把原来的单文件逻辑拆到了多个位置

### 步骤 3: 做四类分类判断

对每个上游更新都写出一个简短结论:

- 已对齐
- 已增强
- 未迁移
- 不建议直接迁

这一步不应省略，因为它决定后面是“写代码”“更新文档”，还是“什么都不改”。

### 步骤 4: 只迁最小必需行为

如果判断为“未迁移”，移植时应只迁移当前工程真正缺的行为。

不建议:

- 整文件照搬
- 顺手恢复 legacy 的组织方式
- 把多个 framework 层压回一个 legacy 文件里

建议:

- 在现有活跃模块内补行为
- 复用当前工程已有映射、状态同步、回写或总线层
- 把上游改动投影到当前工程的现有接口上

### 步骤 5: 同步更新文档

以下文档应按需要同步维护:

- `docs/migration/151L3_CORRESPONDENCE_TABLE.md`
- `docs/migration/LIGHTING_MIGRATION_FROM_151L3.md`
- `docs/ai/AI_AGENT_USAGE_GUIDE.md`
- 任何本次任务直接修改过结论的 checklist 或 summary 文档

原则:

- 当前状态和建议动作分开写
- 已对齐 / 已增强 / 未迁移 / 不建议迁 这四类标签要保持一致

## 建议输出格式

每次处理 `151_l3` 更新时，建议至少输出下面四项:

1. 上游更新摘要
2. 当前工程活跃落点
3. 分类结论
4. 最小移植动作

推荐模板:

```text
上游更新:
- 151_l3 中哪个文件/行为发生了什么变化

当前工程落点:
- 这个行为在当前工程实际落在哪条活跃链路上

分类结论:
- 已对齐 / 已增强 / 未迁移 / 不建议直接迁

动作建议:
- 如果需要移植，给出最小改动面
```

## 推荐与 Agent 配合的使用方式

### 方式 1: 直接使用 agent

选择 `Aputure 151L3 Porting`，适合连续处理一批上游更新。

适合场景:

- 连续比对多个文件
- 一边分析一边落代码
- 同时更新迁移表和对应表

### 方式 2: 使用 prompt

使用 `Port 151L3 Update` prompt，适合单次任务。

适合场景:

- 某个 commit 的一次性对比
- 某个功能点的单独同步判断

## 常见误区

### 误区 1: 同名文件就是同一职责

不成立。

例如 `151_l3/main/app_light.c` 的职责在当前工程中已经被 `app_light + light_control_bus + facade + state_store` 拆开。

### 误区 2: 当前工程没保留某个 legacy 文件名，就等于没迁移

不成立。

很多能力已经拆分迁移，只是不再以原文件名存在。

### 误区 3: 只要 legacy 更新了，当前工程就应同步

不成立。

如果当前工程已经增强实现，或者已有更高层替代，就不应为了“看起来同步”而回退结构。

### 误区 4: 只改代码，不改迁移文档

不建议。

这个仓库当前已经进入“持续迁移 + 持续重构”并存阶段，不更新文档很快就会失真。

## 当前最常见的活跃落点

遇到下面这些任务时，优先从对应位置开始查:

| 上游主题 | 当前工程优先落点 |
|---|---|
| 本地灯控 | `components/app/local_output/`、`main/app/app_light.c`、`main/light/*` |
| RS485 主站 | `main/app/app_rs485_master.c` |
| Endpoint 2 / Matter 回写 | `main/DeviceCallbacks.cpp` |
| PWM / `Factory_RGBWW` | `components/app/local_output/`、`main/app/app_rs485_master.c` |
| 点光源固件升级 | `main/proto/point_light_firmware.*`、`main/app/app_rs485_master.c` |
| 文档对照 | `docs/migration/151L3_CORRESPONDENCE_TABLE.md` |

## 实战短样例

下面这条样例对应一次已经实际执行过的上游更新移植，可直接作为后续任务的最小参考模板。

### 样例: 151_l3 提交 9ed22c0 的 RS485 重连回灌行为

上游更新:

- 提交 `9ed22c0` 在 `151_l3/main/app_rs485_master.c` 中补了一个关键子行为:
- 当主站检测到从机重新连上后，不是只恢复 connected 状态，而是先把当前开关状态和当前灯态重新下发给从机。

当前工程落点:

- 当前工程的真实落点仍然是 `main/app/app_rs485_master.c`。
- 但状态源已经不是 legacy 的 `temp_db` 直读，而是当前工程的 `state_store`。
- 因此不能照搬上游实现，必须把“回灌行为”投影到当前工程已有的 `state_store + rs485_master_send_switch + rs485_master_send_light_ctrl` 组合上。

分类结论:

- 文件级判断: 当前工程的 `app_rs485_master.c` 已增强，不属于“整文件未迁移”。
- 子行为级判断: “重连后回灌当前状态”这一点在处理前属于未迁移。

最小移植动作:

1. 在 `main/app/app_rs485_master.c` 内新增一个小型辅助函数，专门负责“从 state_store 读取 power/light_ctrl 并重新下发给从机”。
2. 只在三个连接恢复点调用它:
	- 首次连通后
	- 轮询检测到重连后
	- 收到未请求上报但此前处于 disconnected 时
3. 不回退到 legacy 的 `temp_db` 读写方式。
4. 不改 `main/main.cpp`、`components/app/local_output/`、`DeviceCallbacks.cpp` 的现有骨架。

结果:

- 当前工程已补齐这条行为缺口。
- 文档也已同步回写到 `docs/migration/151L3_CORRESPONDENCE_TABLE.md`。
- 这条样例说明: 面对 `151_l3` 新更新时，应该优先做“子行为级分类 + 当前活跃落点投影”，而不是直接按同名文件覆盖。

## 最后建议

以后凡是“`151_l3` 又更新了，要不要同步到当前工程”这类任务，建议默认按下面顺序做:

1. 用 `Aputure 151L3 Porting` agent 做初步分类
2. 确认当前工程活跃落点
3. 只迁移最小缺失行为
4. 回写迁移文档

这样可以长期保持当前工程持续吸收上游更新，同时不破坏已经形成的 framework 结构。