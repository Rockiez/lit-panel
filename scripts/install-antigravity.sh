#!/usr/bin/env bash
#
# install-antigravity.sh — 把 lit-panel 的评审 skill 安装到 Google Antigravity 的技能目录。
#
# Google Antigravity 的技能发现方式包括：
# 1. 全局配置：~/.gemini/config/skills/<skill_name>/
# 2. 工作区配置：.agents/skills/<skill_name>/ 或通过 .agents/skills.json 显式声明
#
# 本脚本默认将本仓库的 skills/lit-panel/ 复制到 ~/.gemini/config/skills/lit-panel/。
# 传入 --workspace 参数时，复制到当前工作区的 .agents/skills/lit-panel/。
#
# 用法：
#   ./scripts/install-antigravity.sh              # 安装到全局目录 (~/.gemini/config/skills/lit-panel)
#   ./scripts/install-antigravity.sh --workspace  # 安装到工作区目录 (.agents/skills/lit-panel)
#   ./scripts/install-antigravity.sh -y           # 非交互模式（已存在时自动覆盖）
#
# 幂等性：若目标目录已存在，会先询问是否覆盖，默认（直接回车）为否，不会静默覆盖已有安装。

set -euo pipefail

# 脚本自身所在目录（无论从哪个工作目录调用都能正确定位仓库根）。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SRC="${REPO_ROOT}/skills/lit-panel"
TARGET_MODE="global"
FORCE=false

# 解析命令行参数
for arg in "$@"; do
  case "${arg}" in
    --workspace|-w)
      TARGET_MODE="workspace"
      ;;
    --global|-g)
      TARGET_MODE="global"
      ;;
    -y|--force|-f)
      FORCE=true
      ;;
    -h|--help)
      echo "用法: $0 [--global|--workspace] [-y|--force]"
      echo "  --global    安装到全局技能目录 (~/.gemini/config/skills/lit-panel, 默认)"
      echo "  --workspace 安装到项目工作区目录 (.agents/skills/lit-panel)"
      echo "  -y, --force 已存在目标时直接覆盖，不提示确认"
      exit 0
      ;;
    *)
      echo "未知参数: ${arg}" >&2
      exit 1
      ;;
  esac
done

if [ "${TARGET_MODE}" = "workspace" ]; then
  DEST_DIR="${REPO_ROOT}/.agents/skills"
else
  DEST_DIR="${HOME}/.gemini/config/skills"
fi

DEST="${DEST_DIR}/lit-panel"

# 前置检查：源 skill 目录必须存在且包含 SKILL.md。
if [ ! -f "${SRC}/SKILL.md" ]; then
  echo "错误：未找到 ${SRC}/SKILL.md，无法安装。" >&2
  echo "请确认在完整的 lit-panel 仓库内运行本脚本。" >&2
  exit 1
fi

mkdir -p "${DEST_DIR}"

# 已存在同名目标时，先确认是否覆盖，避免静默覆盖用户的本地修改。
if [ -e "${DEST}" ]; then
  if [ "${FORCE}" = true ]; then
    rm -rf "${DEST}"
  else
    echo "检测到已存在：${DEST}"
    read -r -p "是否覆盖？[y/N] " REPLY
    case "${REPLY}" in
      [yY]|[yY][eE][sS])
        rm -rf "${DEST}"
        ;;
      *)
        echo "已取消，未做任何改动。"
        exit 0
        ;;
    esac
  fi
fi

cp -r "${SRC}" "${DEST}"

echo ""
echo "已安装：${SRC} -> ${DEST}"
echo ""
echo "验证指引："
echo "  1. 确认文件已就位：ls -la \"${DEST}\""
echo "  2. 确认 frontmatter 完整：head -n 5 \"${DEST}/SKILL.md\""
echo "  3. 在 Antigravity (IDE / CLI / 2.0) 中开启新会话，输入："
echo "     '帮我对 <文章路径> 进行文学评审' 或 '/lit-review <文章路径>'"
echo "  4. Antigravity 会自动通过 invoke_subagent 并发派发 11 席评审员，"
echo "     在物理隔离的独立上下文中完成互盲评测与机械核验合成。"
