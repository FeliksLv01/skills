---
name: lookin
description: "通过 Lookin MCP 在运行时检查和调试 iOS 应用视图层级。适用场景：(1) 检查 UIView 是否正确渲染，(2) 查看视图属性、frame、bounds、文本、颜色、约束，(3) 按 class/text/oid 搜索视图，(4) 探索某个 oid 的子树，(5) 诊断 iOS 布局问题，尤其是可见但 frame 为 0、文本非空但宽高为 0、子视图越界，(6) 验证视图层级扁平化/优化效果，(7) 列出 ViewController，(8) 截取单个视图截图。"
mcp:
  lookin:
    type: remote
    url: http://127.0.0.1:47199/mcp
---

# Lookin - iOS 运行时视图检查器

## 概述

Lookin 是一个 iOS UI 检查工具（类似 Reveal）。本 skill 通过 Lookin MCP Server 连接正在运行的 iOS App，实时检查视图层级、属性、约束、文本、布局异常，并在必要时截取视图截图。

**前置条件**：iOS App 必须在模拟器或真机上运行并集成 Lookin 框架，且 Lookin MCP Server 运行在 `http://127.0.0.1:47199/mcp`。

**重要约束**：`oid` 只在当前 hierarchy snapshot 内有效。调用 `reload_hierarchy` 后，旧 `oid` 可能失效或指向不同节点。刷新后必须重新 `search_views`，或用 `find_similar_views` 按 class/frame/text 等线索关联新节点。

## 可用 MCP 工具

所有工具通过 `skill_mcp(mcp_name="lookin", tool_name="<name>", arguments='{...}')` 调用。

### 连接与状态

| 工具 | 说明 | 参数 |
|------|------|------|
| `get_status` | 检查 Lookin Server 是否已连接 iOS App，以及是否已有 hierarchy 数据 | 无 |
| `get_app_info` | 获取 App 名、Bundle ID、设备、系统版本、屏幕尺寸 | 无 |
| `list_apps` | 列出已连接 App | 无 |

### 视图层级

| 工具 | 说明 | 参数 |
|------|------|------|
| `get_hierarchy` | 获取当前 hierarchy snapshot，支持过滤、限制数量和轻量输出 | `flat`（bool，可选）；`maxDepth`（int，可选）；`rootOid`（int，可选）；`classFilter`（string，可选）；`textFilter`（string，可选）；`limit`（int，可选）；`compact`（bool，可选） |
| `get_subtree` | 以某个当前 snapshot 内的 `oid` 为 root 获取子树，适合逐层定位容器和子节点 | `oid`（int，必填）；`maxDepth`（int，可选）；`compact`（bool，可选） |
| `reload_hierarchy` | 从 App 刷新视图层级数据。刷新后旧 `oid` 可能失效 | 无 |
| `find_similar_views` | 用旧 `oid` 在当前 snapshot 中寻找近似节点，基于 class、frame、depth、text 等启发式匹配 | `oid`（int，必填）；`limit`（int，可选，默认 5） |

### 视图检查

| 工具 | 说明 | 参数 |
|------|------|------|
| `get_view` | 通过当前 snapshot 内的 `oid` 获取视图摘要：class、text、frame、bounds、hidden、alpha、父子关系、class chain | `oid`（int，必填） |
| `get_view_attributes` | 获取完整属性组、事件、约束，并额外提供稳定的 `summary` 字段 | `oid`（int，必填） |
| `search_views` | 按 class、文本或 oid 搜索视图。文本搜索应覆盖 UILabel text、attributedText string、UIButton title、accessibilityLabel，以及已加载属性中的字符串 | `query`（string，必填）；`type`（string，可选）：`class` / `text` / `oid` |
| `diagnose_layout` | 聚合常见布局异常：文本非空但宽高为 0、可见节点宽高为 0、子节点超出父 bounds | 无 |

### 截图

| 工具 | 说明 | 参数 |
|------|------|------|
| `get_screenshot` | 获取指定视图的 base64 PNG 截图。只在结构化数据不足以判断视觉结果时使用 | `oid`（int，必填） |

### 视图控制器

| 工具 | 说明 | 参数 |
|------|------|------|
| `list_viewcontrollers` | 列出 ViewController 及其关联 view oid | 无 |

## 关键字段说明

### `oid`

- `oid` 是当前 hierarchy snapshot 内的临时对象 ID。
- `reload_hierarchy` 后，旧 `oid` 不能继续当作稳定引用。
- 如果旧 `oid` 查不到，先用 `find_similar_views`，或根据 class/text/frame 重新搜索。

### `get_view_attributes.summary`

优先读取 `summary`，它比属性组 identifier 更适合机器分析：

```json
{
  "frame": {"x": 0, "y": 0, "width": 0, "height": 20},
  "bounds": {"x": 0, "y": 0, "width": 0, "height": 20},
  "hidden": false,
  "alpha": 1,
  "labelText": "状态：",
  "font": "...",
  "textColor": "...",
  "viewClassChain": ["UILabel", "UIView", "..."],
  "layerClassChain": ["CALayer", "NSObject"]
}
```

如果属性组里的 Layout frame/bounds 为 null，不要直接判断工具没拿到 frame；应看 `summary.frame` 或 `get_view` 的 frame 字段。

### `classChain`

历史字段 `classChain` 可能更接近 layer chain。判断 UIKit 类型时优先看：

- `viewClassChain`
- `layerClassChain`

不要只凭 `classChain = ["CALayer", "NSObject"]` 判断它不是 UILabel/UIView。

## 推荐工作流

### 快速检查 UI 是否正确

```
1. get_status
2. get_hierarchy(compact=true, limit=80)
3. search_views(type="text" 或 type="class")
4. get_view_attributes
5. 必要时 get_screenshot
```

注意：`search_views(type="text")` 返回 0 不能直接等价于“文本没渲染”或“view 没创建”。继续用 class 搜索、`get_subtree` 或 `diagnose_layout` 交叉验证。

### 调试布局问题

```
1. reload_hierarchy
2. diagnose_layout
3. search_views(type="text" / type="class")
4. get_subtree(oid, maxDepth=3, compact=true)
5. get_view_attributes
```

优先看 `diagnose_layout` 是否有：

- `nonempty_text_zero_size`
- `visible_zero_size`
- `child_outside_parent_bounds`

这类结果比单纯搜索文本更能避免误判。例如 UILabel 已创建且 `text = 状态：`，但 width 为 0 时，文本搜索或截图结论都可能误导，布局诊断应直接指出异常。

### 刷新后继续定位同一节点

```
1. reload_hierarchy
2. find_similar_views(oldOid, limit=5)
3. get_view / get_view_attributes 确认候选节点
```

`find_similar_views` 是启发式匹配，不是强身份映射；对候选节点必须再确认 class、frame、text、父子关系。

### 探索复杂子树

```
1. search_views(type="class", query="RCCardEngineMessageContainerView")
2. get_subtree(oid, maxDepth=3, compact=true)
3. 逐层查看 renderedView / children / frame
```

避免一上来 `get_hierarchy(flat=true)` 把几百个 view 全部吐出。优先使用 `rootOid`、`classFilter`、`textFilter`、`limit`、`compact` 缩小信息量。

### 验证视图层级扁平化/优化

```
1. get_hierarchy(flat=true, compact=true, classFilter="UIView", limit=200)
2. 统计返回节点数，与预期对比
3. 必要时 get_subtree 查看局部结构
```

## Agent 行为规范

1. 任何操作前先调用 `get_status`，确认 App 已连接。
2. 如果未连接，提示用户启动集成 Lookin 的 App，并确认 MCP Server 已开启。
3. 默认不要直接拉完整大层级。优先使用 `compact=true`、`limit`、`classFilter`、`textFilter`、`rootOid`。
4. `reload_hierarchy` 后不要复用旧 `oid`；用 `search_views` 或 `find_similar_views` 重新定位。
5. 文本搜索返回 0 时，不要直接下结论。继续检查 `get_view_attributes.summary.labelText`、class 搜索、子树或 `diagnose_layout`。
6. 调布局问题时优先使用 `diagnose_layout`，再对具体节点用 `get_subtree` 和 `get_view_attributes` 深挖。
7. 优先使用结构化数据。只有在属性无法判断图片内容、渐变、圆角裁剪、阴影、视觉对比等问题时才调用 `get_screenshot`。
8. 展示结论时说明关键证据：oid 是否来自当前 snapshot、class、frame、text、hidden、alpha、父子关系、诊断类型。
9. 如果 `get_view_attributes` 的属性组值和 `get_view` 摘要冲突，优先相信 `summary` / `get_view` 中的 frame、bounds、hidden、alpha，并说明属性组可能为空或未稳定映射。
