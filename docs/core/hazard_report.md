# 隐患提报表单 (`form_code = "hazard_report"`)

> 本文档描述 `hazard_report` 表单在 **Form Extraction** 执行链中的 Prompt 模板、字段定义、推断规则与示例。

## 1. 表单字段列表
| 中文名称 | 字段名 | 规则 |
|---|---|---|
| 被检查部门 | `underCheckOrg` | **必填** |
| 检查日期 | `checkDate` | **必填** |
| 隐患级别 | `hiddenTroubleLevel` | **必填** (默认 7) |
| 检查类型 | `checkType` | **必填** (默认 1) |
| 隐患类别 | `hiddenTroubleType` | **必填** |
| 隐患标签 | `illegalType` | **必填** |
| 考核金额(元) | `checkMoney` | 可空 |
| 考核分数 | `checkScore` | 可空 |
| 专题专项 | `specialProject` | 条件必填 |
| 带队领导 | `checkLeader` | 条件必填 |

## 2. 字段枚举值与默认值
### 2.1 隐患级别 (`hiddenTroubleLevel`) — 默认：7
| 值 | 名称 |
|---|---|
| `7` | 一般隐患 |
| `6` | 重点隐患 |
| `5` | 重大隐患 |

### 2.2 检查类型 (`checkType`) — 默认：1
| 值 | 名称 |
|---|---|
| `1` | 日常检查 |
| `3` | 专项检查 |
| `8` | 领导带队检查 |

### 2.3 隐患类别 (`hiddenTroubleType`)
| 值 | 名称 |
|---|---|
| `1` | 交通违章 |
| `2` | 起重 |
| `3` | 煤气安全 |
| `12` | 高处作业 |
| `13` | 其他 |

### 2.4 隐患标签 (`illegalType`)
| 值 | 名称 |
|---|---|
| `1` | 人的不安全行为 |
| `2` | 物的不安全状态 |
| `3` | 管理缺陷 |
| `4` | 环境因素 |

### 2.5 专题专项 (`specialProject`) — `checkType == 5` 时必填
| 值 | 名称 |
|---|---|
| `1` | 露天矿山安全专项整治 |
| `2` | 煤气专项整治 |

### 2.6 带队领导 (`checkLeader`) — `checkType == 8` 时必填
| 值 | 名称 |
|---|---|
| `1` | 李斌 |
| `2` | 阎骏 |

## 3. Prompt 模板（Jinja2）
以下模板已保存在 `app/core/form_extraction/templates/hazard_report.jinja2`，供执行链动态渲染。

```jinja2
[任务定义]
从用户输入的隐患描述中解析推测出隐患提报表单各个字段的值

# 隐患提报表单字段列表
| 中文名称 | 字段名 | 规则 |
|---|---|
| 被检查部门 | `underCheckOrg` | 必填 |
| 检查日期 | `checkDate` | 必填 |
| 隐患级别 | `hiddenTroubleLevel` | 必填 |
| 检查类型 | `checkType` | 必填 |
| 隐患类别 | `hiddenTroubleType` | 必填 |
| 隐患标签 | `illegalType` | 必填 |
| 考核金额(元) | `checkMoney` | 可空 |
| 考核分数 | `checkScore` | 可空 |
| 专题专项 | `specialProject` | 条件必填 |
| 带队领导 | `checkLeader` | 可空 |

##  字段枚举值

### 隐患级别 (`hiddenTroubleLevel`) - 默认值：7
| 值 | 名称 |
|---|---|
| `7` | 一般隐患 |
| `6` | 重点隐患 |
| `5` | 重大隐患 |

### 检查类型 (`checkType`) - 默认值：1
| 值 | 名称 |
|---|---|
| `1` | 日常检查 |
| `3` | 专项检查 |
| `8` | 领导带队检查 |

### 隐患类别 (`hiddenTroubleType`)
| 值 | 名称 |
|---|---|
| `1` | 交通违章 |
| `2` | 起重 |
| `3` | 煤气安全 |
| `12` | 高处作业 |
| `13` | 其他 |

### 隐患标签 (`illegalType`)
| 值 | 名称 |
|---|---|
| `1` | 人的不安全行为 |
| `2` | 物的不安全状态 |
| `3` | 管理缺陷 |
| `4` | 环境因素 |

### 专题专项 (`specialProject`) - 当checkType为5时必填
| 值 | 名称 |
|---|---|
| `1` | 露天矿山安全专项整治 |
| `2` | 煤气专项整治 |

### 带队领导 (`checkLeader`) - 当checkType为8时必填
| 值 | 名称 |
|---|---|
| `1` | 李斌 |
| `2` | 阎骏 |

[字段推断规则]
# 总体规则
1. 对于必填项，即使用户描述中没有明确提及，你也要去推测出一个可能的值
2. 对于可空项，如果用户描述中没有明确提及，设为空，不要自己去猜测
3. 条件必填表示在一定条件下，它是必填项(你需要去推测可能的值)，否则为可空项目

# 具体字段值推测建议
- 检查日期: YYYYMMDD, 描述中没有提及年份时，默认为今年
- 隐患级别:
    - 考核金额为10,000的一般是违反禁令
    - 考核金额为1,000且无明确说明时，一般是重点隐患
    - 其他情况默认为一般隐患
- 检查类型:
    - 描述中如果出现了"带队领导"中的任一领导名字，说明是领导带队检查
- 专题专项: 检查类型为专项检查或专项整治三年行动时必填
    
[输出格式]
仅输出 JSON，无任何多余文本:
```json
{{
  "underCheckOrg": "",
  "checkDate": "",
  "hiddenTroubleLevel": 7,
  "checkType": 1,
  "hiddenTroubleType": 13,
  "illegalType": 4,
  "checkMoney": null,
  "checkScore": null,
  "specialProject": null,
  "checkLeader": null
}}
```

[用户输入]
{{ user_input }}

请仅输出JSON格式的结果，不要包含任何其他文本。
```

## 4. 字段推断规则（运行时实现）
- **checkDate**：缺少年份 → 补当前年份；中文日期 → 归一化 `YYYYMMDD`。
- **checkMoney/checkScore**：空字符串或 "null" → `None`。
- **条件必填**：
  - `checkType == 5` 时：`specialProject` 不得为空。
  - `checkType == 8` 时：`checkLeader` 不得为空。
- **默认值**：如 LLM 未给出字段，使用默认值或 `null`（可空项）。

## 5. 示例
### 5.1 输入
```
7 月 8 日在炼钢厂转炉车间检查时发现，作业人员未系安全带在高处作业，考核金额 1000 元，由李斌现场带队。
```

### 5.2 期望输出
```json
{
  "underCheckOrg": "炼钢厂转炉车间",
  "checkDate": "20250708",
  "hiddenTroubleLevel": 6,
  "checkType": 8,
  "hiddenTroubleType": 12,
  "illegalType": 1,
  "checkMoney": 1000,
  "checkScore": null,
  "specialProject": null,
  "checkLeader": 1
}
```

## 6. 接入说明
1. 在 `registry.py`：
   ```python
   from .hazard_report import HazardReportExecutor
   registry.register("hazard_report", HazardReportExecutor)
   ```
2. 支持同步 / 异步两种调用方式，详见 [`docs/api/api_task_flow.md`](../api/api_task_flow.md)。 