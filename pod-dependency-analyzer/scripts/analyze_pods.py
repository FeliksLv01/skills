#!/usr/bin/env python3
"""
Podfile.lock 依赖分析工具

用法:
  python3 analyze_pods.py <Podfile.lock路径>                      # 顶层库 + 孤立库概览
  python3 analyze_pods.py <Podfile.lock路径> --tree               # 完整依赖树
  python3 analyze_pods.py <Podfile.lock路径> --why XYUITheme      # 追溯某个库被谁依赖（到顶层）
  python3 analyze_pods.py <Podfile.lock路径> --deps XYEvolver     # 展开某个库的依赖（向下）
  python3 analyze_pods.py <Podfile.lock路径> --orphans            # 只列孤立库
"""

import sys
import re
from collections import defaultdict
from pathlib import Path


def parse_podfile_lock(path: Path):
    """返回 (deps, direct_pods)
    deps: dict[str, list[str]]  每个库直接依赖哪些库（sub-spec 折叠到主库）
    direct_pods: set[str]       Podfile 中直接引入的库
    """
    text = path.read_text(encoding="utf-8")

    # 解析 PODS 段
    pods_section = re.search(r"^PODS:\n(.*?)(?=^\S)", text, re.MULTILINE | re.DOTALL)
    deps: dict[str, list[str]] = {}

    if pods_section:
        current = None
        for line in pods_section.group(1).splitlines():
            # 顶层 pod（2 空格缩进，可能带冒号也可能不带）
            if re.match(r"^  - ", line) and not line.startswith("    "):
                m = re.match(r"^  - (.+?)(?:\s*\(.*?\))?\s*:?\s*$", line)
                if m:
                    name = canonical(m.group(1))
                    if name not in deps:
                        deps[name] = []
                    current = name
                continue

            # 依赖项（4 空格缩进）
            if line.startswith("    - ") and current:
                m = re.match(r"^    - (.+?)(?:\s*[=<>!~].*)?\s*$", line)
                if m:
                    dep = canonical(m.group(1))
                    if dep != current and dep not in deps[current]:
                        deps[current].append(dep)

    # 解析 DEPENDENCIES 段（Podfile 直接引入的库）
    dep_section = re.search(r"^DEPENDENCIES:\n(.*?)(?=^\S)", text, re.MULTILINE | re.DOTALL)
    direct_pods: set[str] = set()
    if dep_section:
        for line in dep_section.group(1).splitlines():
            m = re.match(r"^  - (.+?)(?:\s*[=(].*)?\s*$", line)
            if m:
                direct_pods.add(canonical(m.group(1)))

    return deps, direct_pods


def canonical(name: str) -> str:
    """把 sub-spec 折叠为主库名，如 XYFoundation/Core → XYFoundation"""
    return name.split("/")[0].strip()


def build_reverse(deps: dict[str, list[str]]) -> dict[str, list[str]]:
    """构建反向依赖图：每个库被哪些库依赖"""
    rev: dict[str, list[str]] = defaultdict(list)
    for lib, children in deps.items():
        for child in children:
            if lib not in rev[child]:
                rev[child].append(lib)
    return rev


def find_orphans(deps: dict, direct_pods: set, rev: dict) -> list[str]:
    """找出 Podfile 直接引入但没有任何人依赖它的库（潜在可删除）"""
    return sorted(lib for lib in deps if lib in direct_pods and not rev.get(lib))


def print_tree(lib: str, deps: dict, indent: int = 0, visited: set = None):
    """向下展开依赖树（递归）"""
    if visited is None:
        visited = set()
    prefix = "  " * indent
    if lib in visited:
        print(f"{prefix}{lib} ↩ (已展开)")
        return
    visited = visited | {lib}
    children = sorted(deps.get(lib, []))
    print(f"{prefix}{lib}")
    for child in children:
        print_tree(child, deps, indent + 1, visited)


def print_why(lib: str, rev: dict, direct_pods: set, indent: int = 0, visited: set = None):
    """向上追溯：谁依赖了这个库，直到 Podfile 顶层"""
    if visited is None:
        visited = set()
    prefix = "  " * indent
    if lib in visited:
        print(f"{prefix}{lib} ↩ (已追溯)")
        return
    visited = visited | {lib}
    parents = sorted(rev.get(lib, []))
    tag = " ← [Podfile 直接引入]" if lib in direct_pods else ""
    print(f"{prefix}{lib}{tag}")
    for parent in parents:
        print_why(parent, rev, direct_pods, indent + 1, visited)


def resolve_lib(name: str, deps: dict) -> str:
    """模糊匹配库名，找不到则报错退出"""
    if name in deps:
        return name
    matches = [k for k in deps if name.lower() in k.lower()]
    if not matches:
        print(f"未找到库: {name}")
        sys.exit(1)
    if len(matches) == 1:
        return matches[0]
    print(f"找到多个匹配，请指定完整库名:\n  " + "\n  ".join(matches))
    sys.exit(1)


def cmd_overview(deps, direct_pods, rev):
    roots = sorted(lib for lib in deps if not rev.get(lib))
    print(f"=== 顶层库（共 {len(roots)} 个）===\n")
    for lib in roots:
        tag = "✓ Podfile 直接引入" if lib in direct_pods else "⚠ 间接根节点（未在 Podfile 中直接引入）"
        print(f"  {lib}  [{tag}]")

    print()
    orphans = find_orphans(deps, direct_pods, rev)
    print(f"=== 孤立库 - Podfile 直接引入但无人依赖（共 {len(orphans)} 个，可能可删除）===\n")
    for lib in orphans:
        print(f"  {lib}")

    print(f"\n共解析 {len(deps)} 个库")
    print("\n常用命令:")
    print("  --why <库名>    追溯该库被谁引入（到 Podfile 顶层）")
    print("  --deps <库名>   展开该库的依赖树（向下）")
    print("  --orphans       只列孤立库")
    print("  --tree          完整依赖树（输出较长）")


def cmd_tree(deps, direct_pods, rev):
    roots = sorted(lib for lib in deps if not rev.get(lib))
    print(f"=== 完整依赖树（{len(roots)} 个根节点）===\n")
    for root in roots:
        tag = " [Podfile 直接引入]" if root in direct_pods else " [间接根节点]"
        print(f"▶ {root}{tag}")
        for child in sorted(deps.get(root, [])):
            print_tree(child, deps, indent=1, visited={root})
        print()


def main():
    args = sys.argv[1:]

    if not args or args[0].startswith("--"):
        # 尝试在当前目录找 Podfile.lock
        default = Path.cwd() / "Podfile.lock"
        if not default.exists():
            print("用法: python3 analyze_pods.py <Podfile.lock路径> [选项]")
            sys.exit(1)
        lock_path = default
        flag_args = args
    else:
        lock_path = Path(args[0])
        flag_args = args[1:]

    if not lock_path.exists():
        print(f"找不到文件: {lock_path}")
        sys.exit(1)

    deps, direct_pods = parse_podfile_lock(lock_path)
    rev = build_reverse(deps)

    if "--why" in flag_args:
        idx = flag_args.index("--why")
        target = resolve_lib(flag_args[idx + 1], deps)
        print(f"=== {target} 的依赖来源（向上追溯）===\n")
        print_why(target, rev, direct_pods)

    elif "--deps" in flag_args:
        idx = flag_args.index("--deps")
        target = resolve_lib(flag_args[idx + 1], deps)
        print(f"=== {target} 的依赖展开（向下）===\n")
        print_tree(target, deps)

    elif "--orphans" in flag_args:
        orphans = find_orphans(deps, direct_pods, rev)
        print(f"=== 孤立库（共 {len(orphans)} 个）===\n")
        for lib in orphans:
            print(f"  {lib}")

    elif "--tree" in flag_args:
        cmd_tree(deps, direct_pods, rev)

    else:
        cmd_overview(deps, direct_pods, rev)


if __name__ == "__main__":
    main()
