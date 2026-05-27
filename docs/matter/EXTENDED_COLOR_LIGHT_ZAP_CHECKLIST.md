# Extended Color Light ZAP 当前快照

更新时间: 2026-05-19

## 目的

这份文档不再记录“某次修复时应该勾什么”，而是直接记录当前
[ zap-file/zap-files/rootnode_extendedcolorlight_8lcaaYJVAa.zap ]
中 Extended Color Light 相关 endpoint 的实际配置快照，供后续核对、回归和复制使用。

## 数据来源

- ZAP 文件: zap-file/zap-files/rootnode_extendedcolorlight_8lcaaYJVAa.zap
- 当前构建入口: main/CMakeLists.txt 中的 APP_ZAP_FILE
- 提取口径: 以 .zap 中 isEnabled=1 的 command、included=1 的 attribute 为准
- 标准对照文档:
   - docs/matter/CSA_Docs/Matter Device Library Specification-1.5.pdf
   - docs/matter/CSA_Docs/Matter Application Cluster-v1.5.pdf
   - docs/matter/CSA_Docs/Matter Specification-v1.5.pdf

## CSA 1.5 对照结论

### 总结

根据 CSA 1.5 标准文档对照，当前 zap 中 Endpoint 1 和 Endpoint 2 的 Extended Color Light 配置:

- 已满足 Extended Color Light 设备类型的绝大多数强制 cluster 和 feature 要求。
- 当前不能判定为“完全合规”，主要阻塞项是 Level Control cluster 缺少 MinLevel attribute。
- MaxLevel 当前未包含，但按 cluster 规范它仍是可选项，不作为这次的主阻塞结论。
- Scenes Management 的 provisional 属性属于标准文档明确标注的 provisional 项，不应单独判为设备类型不合规，但认证和工具链输出中仍应继续关注。

### Endpoint 级结论

| Endpoint | 设备类型 | 当前结论 |
|---|---|---|
| 1 | Extended Color Light | 部分合规，存在 1 个明确阻塞项 |
| 2 | Extended Color Light | 部分合规，存在 1 个明确阻塞项 |

补充说明:

- Endpoint 1 和 Endpoint 2 绑定的是两个不同的 Extended Color Light endpoint type。
- 但这两个 endpoint type 在启用的 cluster、command、attribute 名称集合上完全一致。
- 因此标准对照结论对 Endpoint 1 和 Endpoint 2 相同。

## 标准判定依据

### 1. Device Library 对 Extended Color Light 的要求

根据 Matter Device Library Specification 1.5 第 4.4 节:

- Extended Color Light 设备类型 ID 为 0x010D。
- 该设备类型强制要求以下 server cluster:
   - Identify
   - Groups
   - On/Off
   - Level Control
   - Scenes Management
   - Color Control
- 该设备类型还定义了以下关键 element requirement:
   - Identify.TriggerEffect 为 mandatory
   - On/Off 的 Lighting feature 为 mandatory
   - Level Control 的 OnOff feature 为 mandatory
   - Level Control 的 Lighting feature 为 mandatory
   - Level Control 的 CurrentLevel 约束为 1..254
   - Level Control 的 MinLevel 约束为 1
   - Level Control 的 MaxLevel 约束为 254
   - Scenes Management.CopyScene 为 mandatory
   - Color Control 的 XY feature 为 mandatory
   - Color Control 的 ColorTemperature feature 为 mandatory
   - Color Control 的 HueSaturation / EnhancedHue / ColorLoop 为 optional

### 2. Application Cluster 对相关 cluster 的要求

根据 Matter Application Cluster 1.5:

- Identify cluster 的 TriggerEffect 命令存在且可用于设备识别反馈。
- Scenes Management server 若实现，则同 endpoint 上必须实现 Groups server。
- On/Off cluster 的 OffWithEffect、OnWithRecallGlobalScene、OnWithTimedOff 都在规范中定义，适用于 lighting 场景。
- Level Control cluster 中:
   - MinLevel 的 conformance 为 [LT]，即在 Lighting feature 存在时需要实现。
   - MaxLevel 的 conformance 为 O，即 optional。
   - OnLevel 的 conformance 为 M。
   - Options 的 conformance 为 M。
- Color Control cluster 的 feature 表中:
   - XY 为 mandatory feature
   - ColorTemperature 为 mandatory feature
   - HueSaturation、EnhancedHue、ColorLoop 为 optional feature

### 3. Matter Specification 对 provisional 的说明

根据 Matter Specification 1.5:

- provisional 代表规范中已经列出但仍属 provisional 的项。
- Scenes Management 本身出现在标准体系中，provisional 不等于设备类型自动不合规。
- 但认证和实现阶段仍应继续关注工具链、测试项和后续规范版本变化。

## 当前 endpoint 映射

当前 .zap 中共有 3 个 endpoint 实例:

| Endpoint ID | Endpoint Type Index | Endpoint Type Name | 实际设备类型 |
|---|---|---|---|
| 0 | 0 | MA-rootdevice | Root Node |
| 1 | 1 | Anonymous Endpoint Type | Extended Color Light |
| 2 | 2 | Anonymous Endpoint Type | Extended Color Light |

补充说明:

- Endpoint 1 对应的 endpoint type id 是 2。
- Endpoint 2 对应的 endpoint type id 是 3。
- 这两个 Extended Color Light endpoint type 在“启用的 cluster、command、attribute 名称集合”层面完全一致。
- 因此下面的 cluster 清单同时适用于 Endpoint 1 和 Endpoint 2。

## Extended Color Light 设备类型

| 项目 | 当前值 |
|---|---|
| Device Type Name | MA-extendedcolorlight |
| Device Type Code | 269 |
| Profile ID | 259 |

## 当前启用的 server cluster

Extended Color Light endpoint 当前启用了以下 7 个 server cluster:

| Cluster | 当前状态 |
|---|---|
| Identify | 启用 |
| Groups | 启用 |
| On/Off | 启用 |
| Level Control | 启用 |
| Descriptor | 启用 |
| Scenes Management | 启用 |
| Color Control | 启用 |

## 当前 zap 与 CSA 1.5 的逐项对照

| 检查项 | CSA 1.5 要求 | 当前 zap | 判定 |
|---|---|---|---|
| Device Type | 0x010D Extended Color Light | Endpoint 1/2 均为 Extended Color Light | 通过 |
| Identify server | Mandatory | 已启用 | 通过 |
| Groups server | Mandatory | 已启用 | 通过 |
| On/Off server | Mandatory | 已启用 | 通过 |
| Level Control server | Mandatory | 已启用 | 通过 |
| Scenes Management server | Mandatory | 已启用 | 通过 |
| Color Control server | Mandatory | 已启用 | 通过 |
| Identify.TriggerEffect | Mandatory | 已启用 | 通过 |
| On/Off Lighting feature | Mandatory | FeatureMap = 1 | 通过 |
| Level Control OnOff feature | Mandatory | FeatureMap = 3 | 通过 |
| Level Control Lighting feature | Mandatory | FeatureMap = 3 | 通过 |
| Level Control.CurrentLevel | Mandatory with constraint 1..254 | 已启用 | 基本通过 |
| Level Control.MinLevel | Mandatory when Lighting feature exists | 当前未包含 | 不通过 |
| Level Control.MaxLevel | Optional in cluster spec | 当前未包含 | 可接受 |
| Level Control.OnLevel | Mandatory | 已启用 | 通过 |
| Level Control.Options | Mandatory | 已启用 | 通过 |
| Scenes Management.CopyScene | Mandatory | 已启用 | 通过 |
| Color Control.XY feature | Mandatory | FeatureMap = 24 | 通过 |
| Color Control.ColorTemperature feature | Mandatory | FeatureMap = 24 | 通过 |
| Color Control.HueSaturation | Optional | 未启用 | 可接受 |
| Color Control.EnhancedHue | Optional | 未启用 | 可接受 |
| Color Control.ColorLoop | Optional | 未启用 | 可接受 |

### 当前主阻塞项

| 项目 | 当前状态 | 标准依据 | 影响 |
|---|---|---|---|
| Level Control.MinLevel | 未 included | Application Cluster 1.5 中 MinLevel conformance 为 [LT]；Extended Color Light 又强制要求 Level Control 的 Lighting feature | Endpoint 1/2 当前不能判定为完全合规 |

## 最小 ZAP 变更清单

如果目标只是把当前 Endpoint 1 和 Endpoint 2 的 Extended Color Light 配置补到“按 CSA 1.5 可判定合规”的最小状态，当前建议只做 1 项 ZAP 变更。

### 需要修改的对象

| Endpoint | Endpoint Type ID | Cluster | 需要补的项 |
|---|---|---|---|
| 1 | 2 | Level Control | MinLevel attribute |
| 2 | 3 | Level Control | MinLevel attribute |

### 最小变更内容

| 项目 | 当前值 | 目标值 | 是否必须现在处理 |
|---|---|---|---|
| Level Control.MinLevel | 未 included | included | 是 |
| Level Control.MaxLevel | 未 included | 保持不变 | 否 |
| Level Control.FeatureMap | 3 | 保持 3 | 是 |
| Color Control.HueSaturation / EnhancedHue / ColorLoop | 未启用 | 保持不变 | 否 |

### 执行说明

在 ZAP 界面中，对两个 Extended Color Light endpoint type 分别执行相同操作:

1. 打开 Level Control cluster。
2. 在 attributes 列表中找到 MinLevel。
3. 将 MinLevel 勾选为 included。
4. 不要同时为了“看起来完整”去补 MaxLevel、HueSaturation、EnhancedHue、ColorLoop，除非后续工具明确继续报这些项。
5. 保持 Level Control 的 FeatureMap 仍为 3，也就是 OnOff + Lighting 两个 feature 继续开启。

### 预期结果

完成上述最小变更后，Endpoint 1 和 Endpoint 2 的 Extended Color Light 配置应达到以下状态:

- 设备类型强制 cluster 仍保持不变。
- Level Control 的 mandatory feature 仍保持不变。
- 当前唯一明确阻塞项 MinLevel 被补齐。
- 当前文档中的主结论应可从“部分合规，存在 1 个明确阻塞项”收敛到“无已知明确阻塞项，待重新跑工具确认”。

### 暂不建议纳入这轮最小变更的项

| 项目 | 原因 |
|---|---|
| MaxLevel | Application Cluster 1.5 中仍是 optional，不是当前最小合规修复所必需 |
| Color Control 的 HS / EHUE / CL | Extended Color Light 设备类型只强制 XY 和 ColorTemperature |
| Occupancy Sensing client | Device Library 中是 optional |
| Scenes Management 的 provisional 属性 | 属于标准状态标记，不是通过多勾一个 attribute 就能解决的问题 |

### 变更后验证

建议按下面顺序验证:

1. 重新生成 .matter / codegen 产物。
2. 执行 idf.py reconfigure build。
3. 重新观察 Device Type Compliance 输出。
4. 如果 Extended Color Light 相关报错消失，再决定是否继续处理 MaxLevel 或其它非阻塞提示。

### 当前非阻塞观察项

| 项目 | 当前状态 | 说明 |
|---|---|---|
| Level Control.MaxLevel | 未 included | Cluster 规范里是 optional，不单独构成这轮不合规结论 |
| Scenes Management | API maturity = provisional | 会带来标准/工具链提示，但不等于设备类型自动不合规 |
| Color Control 的 HS/EHUE/CL | 未启用 | Device Library 对 Extended Color Light 只要求 XY 和 ColorTemperature mandatory |

## 1. Identify

### Commands

| Command | 方向 | 当前状态 |
|---|---|---|
| Identify | Incoming | 启用 |
| TriggerEffect | Incoming | 启用 |

### Attributes

| Attribute | 当前状态 |
|---|---|
| IdentifyTime | 启用 |
| IdentifyType | 启用 |
| GeneratedCommandList | 启用 |
| AcceptedCommandList | 启用 |
| AttributeList | 启用 |
| FeatureMap | 启用 |
| ClusterRevision | 启用 |

## 2. Groups

### Commands

| Command | 方向 | 当前状态 |
|---|---|---|
| AddGroup | Incoming | 启用 |
| AddGroupResponse | Outgoing | 启用 |
| ViewGroup | Incoming | 启用 |
| ViewGroupResponse | Outgoing | 启用 |
| GetGroupMembership | Incoming | 启用 |
| GetGroupMembershipResponse | Outgoing | 启用 |
| RemoveGroup | Incoming | 启用 |
| RemoveGroupResponse | Outgoing | 启用 |
| RemoveAllGroups | Incoming | 启用 |
| AddGroupIfIdentifying | Incoming | 启用 |

### Attributes

| Attribute | 默认值 |
|---|---|
| NameSupport | 0x00 |
| GeneratedCommandList | 空 |
| AcceptedCommandList | 空 |
| AttributeList | 空 |
| FeatureMap | 0 |
| ClusterRevision | 4 |

## 3. On/Off

### Commands

| Command | 方向 | 当前状态 |
|---|---|---|
| Off | Incoming | 启用 |
| On | Incoming | 启用 |
| Toggle | Incoming | 启用 |
| OffWithEffect | Incoming | 启用 |
| OnWithRecallGlobalScene | Incoming | 启用 |
| OnWithTimedOff | Incoming | 启用 |

### Attributes

| Attribute | 当前状态 | 默认值 |
|---|---|---|
| OnOff | 启用 | 空 |
| GlobalSceneControl | 启用 | 空 |
| OnTime | 启用 | 空 |
| OffWaitTime | 启用 | 空 |
| StartUpOnOff | 启用 | 空 |
| GeneratedCommandList | 启用 | 空 |
| AcceptedCommandList | 启用 | 空 |
| AttributeList | 启用 | 空 |
| FeatureMap | 启用 | 1 |
| ClusterRevision | 启用 | 6 |

## 4. Level Control

### Commands

| Command | 方向 | 当前状态 |
|---|---|---|
| MoveToLevel | Incoming | 启用 |
| Move | Incoming | 启用 |
| Step | Incoming | 启用 |
| Stop | Incoming | 启用 |
| MoveToLevelWithOnOff | Incoming | 启用 |
| MoveWithOnOff | Incoming | 启用 |
| StepWithOnOff | Incoming | 启用 |
| StopWithOnOff | Incoming | 启用 |

### Attributes

| Attribute | 当前状态 | 默认值 |
|---|---|---|
| CurrentLevel | 启用 | 空 |
| RemainingTime | 启用 | 空 |
| Options | 启用 | 空 |
| OnLevel | 启用 | 空 |
| StartUpCurrentLevel | 启用 | 空 |
| GeneratedCommandList | 启用 | 空 |
| AcceptedCommandList | 启用 | 空 |
| AttributeList | 启用 | 空 |
| FeatureMap | 启用 | 3 |
| ClusterRevision | 启用 | 6 |

### 当前未包含的常见属性

当前 .zap 中以下常见 Level Control 属性没有被 included:

- MinLevel
- MaxLevel

这意味着当前文档口径应为“MinLevel 和 MaxLevel 都未包含”，而不是仅仅“MinLevel 禁用”。

## 5. Descriptor

### Commands

当前未配置 Descriptor 命令。

### Attributes

| Attribute | 当前状态 |
|---|---|
| DeviceTypeList | 启用 |
| ServerList | 启用 |
| ClientList | 启用 |
| PartsList | 启用 |
| GeneratedCommandList | 启用 |
| AcceptedCommandList | 启用 |
| AttributeList | 启用 |
| FeatureMap | 启用 |
| ClusterRevision | 启用 |

## 6. Scenes Management

### Cluster 状态

| 项目 | 当前值 |
|---|---|
| Cluster | Scenes Management |
| API Maturity | provisional |
| FeatureMap 默认值 | 0 |
| SceneTableSize 默认值 | 16 |
| ClusterRevision 默认值 | 1 |

### Commands

| Command | 方向 | 当前状态 |
|---|---|---|
| AddScene | Incoming | 启用 |
| AddSceneResponse | Outgoing | 启用 |
| ViewScene | Incoming | 启用 |
| ViewSceneResponse | Outgoing | 启用 |
| RemoveScene | Incoming | 启用 |
| RemoveSceneResponse | Outgoing | 启用 |
| RemoveAllScenes | Incoming | 启用 |
| RemoveAllScenesResponse | Outgoing | 启用 |
| StoreScene | Incoming | 启用 |
| StoreSceneResponse | Outgoing | 启用 |
| RecallScene | Incoming | 启用 |
| GetSceneMembership | Incoming | 启用 |
| GetSceneMembershipResponse | Outgoing | 启用 |
| CopyScene | Incoming | 启用 |
| CopySceneResponse | Outgoing | 启用 |

### Attributes

| Attribute | 当前状态 | 默认值 |
|---|---|---|
| SceneTableSize | 启用 | 16 |
| FabricSceneInfo | 启用 | 空 |
| GeneratedCommandList | 启用 | 空 |
| AcceptedCommandList | 启用 | 空 |
| AttributeList | 启用 | 空 |
| FeatureMap | 启用 | 0 |
| ClusterRevision | 启用 | 1 |

## 7. Color Control

### Commands

| Command | 方向 | 当前状态 |
|---|---|---|
| MoveToColor | Incoming | 启用 |
| MoveColor | Incoming | 启用 |
| StepColor | Incoming | 启用 |
| MoveToColorTemperature | Incoming | 启用 |
| StopMoveStep | Incoming | 启用 |
| MoveColorTemperature | Incoming | 启用 |
| StepColorTemperature | Incoming | 启用 |

### Attributes

| Attribute | 当前状态 | 默认值 |
|---|---|---|
| RemainingTime | 启用 | 0x0000 |
| CurrentX | 启用 | 0x616B |
| CurrentY | 启用 | 0x607D |
| ColorTemperatureMireds | 启用 | 0x00FA |
| ColorMode | 启用 | 0x01 |
| Options | 启用 | 0x00 |
| NumberOfPrimaries | 启用 | 空 |
| EnhancedColorMode | 启用 | 0x01 |
| ColorCapabilities | 启用 | 0x0000 |
| ColorTempPhysicalMinMireds | 启用 | 0x0000 |
| ColorTempPhysicalMaxMireds | 启用 | 0xFEFF |
| CoupleColorTempToLevelMinMireds | 启用 | 空 |
| StartUpColorTemperatureMireds | 启用 | 空 |
| GeneratedCommandList | 启用 | 空 |
| AcceptedCommandList | 启用 | 空 |
| AttributeList | 启用 | 空 |
| FeatureMap | 启用 | 24 |
| ClusterRevision | 启用 | 7 |

### 当前配置特征

从命令集合看，当前 Color Control 主要开启的是 XY 与 Color Temperature 相关控制命令，没有看到 Hue/Saturation 那组单独命令被勾选。

## 与旧版清单相比需要纠正的点

旧版文档里有几处已经不再准确，这里直接标明:

| 旧口径 | 当前 zap 实际情况 |
|---|---|
| 只针对 Endpoint 1 | 当前 Endpoint 1 和 Endpoint 2 都是 Extended Color Light |
| Scenes Management.FeatureMap 默认值 1 | 当前实际默认值是 0 |
| Level Control 里 MaxLevel 启用 | 当前 .zap 未包含 MaxLevel |
| Color Control 只建议“保持默认，不额外裁剪” | 当前可以明确列出实际启用的 7 个命令和 18 个属性 |
| 只要 cluster 勾齐就能视为合规 | 还需要检查 device type element requirement，当前 MinLevel 仍是阻塞项 |

## 复用建议

如果后续要继续复制或修改 Extended Color Light endpoint，建议按下面顺序核对:

1. 先确认 endpoint 实例是否仍然是 Endpoint 1 和 Endpoint 2。
2. 再确认这两个 endpoint type 的 cluster/command/attribute 名称集合是否仍一致。
3. 优先复核 Identify、On/Off、Level Control、Scenes Management、Color Control 五个 cluster。
4. 特别关注以下容易写错的点:
   - TriggerEffect 必须存在
   - On/Off 三个扩展命令必须存在
   - Scenes Management 必须启用且 API maturity 仍是 provisional
   - Level Control 按 CSA 1.5 至少还应补上 MinLevel
   - MaxLevel 当前虽未包含，但按 cluster 规范仍属 optional
   - Color Control 当前走的是 XY/Color Temperature 命令集
5. 修改 .zap 后仍建议执行 idf.py reconfigure build，避免 codegen 与链接产物不同步。

## 建议动作

如果目标是按当前 CSA 1.5 文档把 Endpoint 1 和 Endpoint 2 拉到“可判定合规”的状态，建议优先处理:

1. 在两个 Extended Color Light endpoint type 的 Level Control cluster 中补回 MinLevel attribute。
2. 补完后重新核对 Level Control 的 FeatureMap 仍保持 OnOff + Lighting。
3. 执行 idf.py reconfigure build，并重新看 Device Type Compliance 输出是否还报 Extended Color Light 相关问题。
4. 如果后续认证工具仍继续对 MaxLevel 提示，再结合实际测试工具版本决定是否一并补上，但从 1.5 cluster 文档本身看它不是当前主阻塞项。
