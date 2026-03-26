---
name: pod-dependency-analyzer
description: "分析 iOS 项目的 Podfile.lock 依赖关系。适用场景：(1) 分析完整依赖树，(2) 追溯某个库被哪些库引入（--why），(3) 展开某个库依赖了什么（--deps），(4) 找出可能多余的孤立库（--orphans），(5) 分析 IPA 体积、移除无用依赖、解决符号冲突等场景。"
---

# Pod Dependency Analyzer

## 使用时机

当用户提出以下问题时，使用本 skill：

- "为什么 IPA 里有 SomeLib？"
- "某个库是谁引进来的？"
- "有哪些库可以删掉？"
- "帮我分析一下依赖树"
- "这个库依赖了什么？"

## 脚本位置

```
{SKILL_DIR}/scripts/analyze_pods.py
```

其中 `{SKILL_DIR}` 为本 skill 所在目录：`/Users/lvyou4/.agents/skills/pod-dependency-analyzer`

## 用法

```bash
# 概览：顶层库 + 孤立库（默认）
python3 {SKILL_DIR}/scripts/analyze_pods.py <Podfile.lock路径>

# 追溯某个库被谁引入，直到 Podfile 顶层
python3 {SKILL_DIR}/scripts/analyze_pods.py <Podfile.lock路径> --why <库名>

# 展开某个库的完整依赖（向下）
python3 {SKILL_DIR}/scripts/analyze_pods.py <Podfile.lock路径> --deps <库名>

# 只列出孤立库（Podfile 直接引入但无人依赖）
python3 {SKILL_DIR}/scripts/analyze_pods.py <Podfile.lock路径> --orphans

# 打印完整依赖树（输出较长）
python3 {SKILL_DIR}/scripts/analyze_pods.py <Podfile.lock路径> --tree
```

如果在项目根目录（`Podfile.lock` 所在目录）执行，可省略路径：

```bash
python3 {SKILL_DIR}/scripts/analyze_pods.py --why <库名>
```

## 工作流

### 场景一：移除某个库

1. 运行 `--why <库名>` 找出所有引入来源
2. 对每个来源递归追溯，找到顶层 Podfile 直接引入的库
3. 确认这些顶层库在项目中是否有代码引用：
   ```bash
   grep -rn "import <库名>" Runner/ Submodules/ --include="*.swift" --include="*.m" --include="*.h" -l
   ```
4. 确认本地 podspec 是否有 dependency：
   ```bash
   grep -rn "dependency.*<库名>" Submodules/ --include="*.podspec"
   ```
5. 若无引用，从 Podfile 删除对应行，重新 `pod install`

### 场景二：查找可删除的库

1. 运行 `--orphans` 列出孤立库
2. 对每个孤立库进行代码引用搜索（步骤同上）
3. 批量删除确认无用的库

### 场景三：理解某个库的依赖

1. 运行 `--deps <库名>` 查看完整依赖树
2. 重点关注体积大的子依赖（如 Assets.car、XCFramework）

## 输出解读

| 标记 | 含义 |
|------|------|
| `✓ Podfile 直接引入` | 该库在 Podfile 中有直接 `pod "..."` 行 |
| `⚠ 间接根节点` | 没有其他库依赖它，但也不在 Podfile 中（异常情况） |
| `← [Podfile 直接引入]` | `--why` 追溯时，表示已到达顶层 |
| `↩ (已展开)` | 防止循环依赖的标记 |

## 注意事项

- 脚本将 sub-spec 自动折叠为主库名（如 `SomeLib/Core` → `SomeLib`）
- 支持模糊匹配库名（大小写不敏感），有多个匹配时会列出供选择
- 只依赖 Python 3 标准库，无需安装额外依赖
