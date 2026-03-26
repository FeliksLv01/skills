---
name: lookin
description: "通过 Lookin MCP 在运行时检查和调试 iOS 应用视图层级。适用场景：(1) 检查 UIView 是否正确渲染，(2) 查看视图属性（frame、backgroundColor、constraints 等），(3) 按类名或文本搜索特定视图，(4) 截取单个视图的截图，(5) 调试 iOS 模拟器中的布局问题，(6) 验证视图层级扁平化/优化效果，(7) 列出视图控制器，(8) 任何「看一下界面」「检查 UI」的请求。"
mcp:
  lookin:
    type: remote
    url: http://127.0.0.1:47199/mcp
---

# Lookin - iOS 运行时视图检查器

## 概述

Lookin 是一个 iOS UI 检查工具（类似 Reveal）。本 skill 通过 Lookin MCP 服务器连接到正在运行的 iOS 应用，实时检查视图层级、视图属性、约束，以及截取视图截图。

**前置条件**：iOS 应用必须在模拟器（或真机）上运行并集成了 Lookin 框架，且 Lookin MCP 服务器运行在 `http://127.0.0.1:47199/mcp`。

## 可用 MCP 工具

所有工具通过 `skill_mcp(mcp_name="lookin", tool_name="<name>", arguments='{...}')` 调用。

### 连接与状态

| 工具 | 说明 | 参数 |
|------|------|------|
| `get_status` | 检查 Lookin 服务器是否已连接 iOS 应用 | 无 |
| `get_app_info` | 获取应用名、Bundle ID、设备、系统版本、屏幕尺寸 | 无 |
| `list_apps` | 列出所有已连接的 iOS 应用 | 无 |

### 视图层级

| 工具 | 说明 | 参数 |
|------|------|------|
| `get_hierarchy` | 获取完整视图树 | `flat`（bool，可选）：扁平数组或树形；`maxDepth`（int，可选）：深度限制 |
| `reload_hierarchy` | 从应用刷新视图层级数据 | 无 |

### 视图检查

| 工具 | 说明 | 参数 |
|------|------|------|
| `get_view` | 通过 oid 获取视图详细信息 | `oid`（int，必填） |
| `get_view_attributes` | 获取全部属性：布局、AutoLayout、属性、手势、约束 | `oid`（int，必填） |
| `search_views` | 按类名、文本或 oid 搜索视图 | `query`（string，必填）；`type`（string，可选）："class" / "text" / "oid" |

### 截图

| 工具 | 说明 | 参数 |
|------|------|------|
| `get_screenshot` | 获取指定视图的 base64 PNG 截图 | `oid`（int，必填） |

### 视图控制器

| 工具 | 说明 | 参数 |
|------|------|------|
| `list_viewcontrollers` | 列出所有视图控制器及其类名和对应视图的 oid | 无 |

## 工作流

### 快速检查（UI 是否正确？）

```
1. get_status          → 确认应用已连接
2. get_hierarchy       → 获取视图树概览
3. search_views        → 按类名或文本查找目标视图
4. get_view_attributes → 检查 frame、属性、约束
   （通常到这里就够了 —— 如果数据已能回答问题，到此为止）
5. get_screenshot      → 仅在需要验证视觉外观时才调用
```

### 调试布局问题

```
1. reload_hierarchy    → 刷新获取最新状态
2. search_views        → 找到有问题的视图
3. get_view_attributes → 检查 frame、约束、属性
4. get_view            → 获取类继承链和父子关系
```

### 验证视图层级扁平化/优化

```
1. get_hierarchy(flat=true)  → 获取所有视图的扁平列表
2. 统计 UIView 节点数，与预期对比
3. search_views(type="class", query="UIView") → 查找所有纯 UIView
4. 与组件树对比，验证被裁剪的节点确实已不存在
```

## Agent 行为规范

1. **任何操作前先调用 `get_status`**，确认应用已连接。
2. 如果未连接，提示用户在模拟器中启动集成了 Lookin 的应用。
3. 检查视图时，先用 `get_hierarchy` 获取概览，再用 `get_view` / `get_view_attributes` 对特定 oid 深入查看。
4. 当用户说「看一下界面」「检查一下 UI」时，使用 `get_hierarchy` + `search_views` 分析实时 UI。
5. **优先使用结构化数据，而非截图。** `get_view_attributes` 能回答关于 frame、颜色、可见性、约束、文本内容等的绝大多数问题。仅在以下情况使用 `get_screenshot`：
   - 用户明确要求「看一下」「给我看看」某个视图的视觉外观。
   - 需要验证仅靠属性无法判断的渲染效果（如图片内容、渐变渲染、圆角裁剪、阴影效果等）。
   - 用户要求对比修改前后的视觉状态。
6. **默认不要调用 `get_screenshot`**，将其视为高成本操作。
7. 如果 UI 可能在上次获取后发生了变化，先调用 `reload_hierarchy` 刷新。
8. 简洁地呈现结果：视图数量、层级深度、关键属性、异常情况。
