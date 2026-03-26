#!/bin/bash
#
# Skills 安装脚本
# 
# 用法: 
#   ./install.sh                              # 安装所有 skills
#   ./install.sh redcity-ios-log-analysis     # 安装指定 skill
#   ./install.sh --link                       # 使用软链接安装（推荐，方便更新）
#   ./install.sh --link redcity-ios-log-analysis
#   ./install.sh --uninstall                  # 卸载所有 skills
#   ./install.sh --uninstall redcity-ios-log-analysis
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.agents/skills"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 获取所有可用的 skills
list_skills() {
    local skills=()
    for dir in "$SCRIPT_DIR"/*/; do
        if [ -f "${dir}SKILL.md" ]; then
            skills+=("$(basename "$dir")")
        fi
    done
    echo "${skills[@]}"
}

# 安装单个 skill (复制方式)
install_skill_copy() {
    local skill_name="$1"
    local skill_path="$SCRIPT_DIR/$skill_name"
    local target_path="$SKILLS_DIR/$skill_name"

    if [ ! -d "$skill_path" ]; then
        log_error "Skill not found: $skill_name"
        return 1
    fi

    if [ ! -f "$skill_path/SKILL.md" ]; then
        log_error "Invalid skill (missing SKILL.md): $skill_name"
        return 1
    fi

    mkdir -p "$SKILLS_DIR"

    # 如果已存在，先删除
    if [ -d "$target_path" ] || [ -L "$target_path" ]; then
        rm -rf "$target_path"
    fi

    cp -r "$skill_path" "$target_path"
    log_info "Installed (copy): $skill_name"
}

# 安装单个 skill (软链接方式)
install_skill_link() {
    local skill_name="$1"
    local skill_path="$SCRIPT_DIR/$skill_name"
    local target_path="$SKILLS_DIR/$skill_name"

    if [ ! -d "$skill_path" ]; then
        log_error "Skill not found: $skill_name"
        return 1
    fi

    if [ ! -f "$skill_path/SKILL.md" ]; then
        log_error "Invalid skill (missing SKILL.md): $skill_name"
        return 1
    fi

    mkdir -p "$SKILLS_DIR"

    # 如果已存在，先删除
    if [ -d "$target_path" ] || [ -L "$target_path" ]; then
        rm -rf "$target_path"
    fi

    ln -s "$skill_path" "$target_path"
    log_info "Installed (link): $skill_name -> $skill_path"
}

# 卸载单个 skill
uninstall_skill() {
    local skill_name="$1"
    local target_path="$SKILLS_DIR/$skill_name"

    if [ -d "$target_path" ] || [ -L "$target_path" ]; then
        rm -rf "$target_path"
        log_info "Uninstalled: $skill_name"
    else
        log_warn "Not installed: $skill_name"
    fi
}

# 显示帮助
show_help() {
    echo "Skills Installer"
    echo ""
    echo "Usage:"
    echo "  ./install.sh [options] [skill-name]"
    echo ""
    echo "Options:"
    echo "  --link, -l       Use symbolic links (recommended for easy updates)"
    echo "  --uninstall, -u  Uninstall skills"
    echo "  --list           List available skills"
    echo "  --help, -h       Show this help"
    echo ""
    echo "Examples:"
    echo "  ./install.sh                    # Install all skills (copy)"
    echo "  ./install.sh --link             # Install all skills (symlink)"
    echo "  ./install.sh --link skill-name  # Install specific skill (symlink)"
    echo "  ./install.sh --uninstall        # Uninstall all skills"
    echo ""
    echo "Tip: Use --link for easy updates. After 'git pull', skills auto-update."
}

# 主逻辑
main() {
    local use_link=false
    local uninstall=false
    local skill_name=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --link|-l)
                use_link=true
                shift
                ;;
            --uninstall|-u)
                uninstall=true
                shift
                ;;
            --list)
                echo "Available skills:"
                for skill in $(list_skills); do
                    echo "  - $skill"
                done
                exit 0
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                skill_name="$1"
                shift
                ;;
        esac
    done

    echo "========================================"
    echo "  Skills Installer"
    echo "========================================"
    echo ""

    local skills
    if [ -n "$skill_name" ]; then
        skills="$skill_name"
    else
        skills=$(list_skills)
    fi

    if [ -z "$skills" ]; then
        log_error "No skills found in $SCRIPT_DIR"
        exit 1
    fi

    if $uninstall; then
        log_step "Uninstalling skills..."
        for skill in $skills; do
            uninstall_skill "$skill"
        done
    else
        if $use_link; then
            log_step "Installing skills (symlink mode)..."
            log_info "Skills will auto-update after 'git pull'"
        else
            log_step "Installing skills (copy mode)..."
            log_warn "Re-run this script after 'git pull' to update"
        fi
        echo ""

        for skill in $skills; do
            if $use_link; then
                install_skill_link "$skill"
            else
                install_skill_copy "$skill"
            fi
        done
    fi

    echo ""
    echo "========================================"
    log_info "Done! Skills directory: $SKILLS_DIR"
    echo "========================================"
}

main "$@"
