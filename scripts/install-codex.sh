#!/usr/bin/env bash
#
# install-codex.sh — 把 lit-panel 的评审 skill 安装到 Codex 的本地 skill 目录。
#
# Codex 没有 Claude Code 那样的 plugin 机制，其技能发现方式是扫描
# ~/.agents/skills/ 下的子目录（每个子目录含 SKILL.md）。本脚本只做一件事：
# 把本仓库的 skills/lit-panel/ 整目录复制到 ~/.agents/skills/lit-panel/。
#
# 用法：
#   ./scripts/install-codex.sh
#
# 幂等性：若目标目录已存在，会先询问是否覆盖，默认（直接回车）为否，
# 不会静默覆盖已有安装。

set -euo pipefail

# 脚本自身所在目录（无论从哪个工作目录调用都能正确定位仓库根）。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SRC="${REPO_ROOT}/skills/lit-panel"
DEST_DIR="${HOME}/.agents/skills"
DEST="${DEST_DIR}/lit-panel"

# 前置检查：源 skill 目录必须包含说明与可独立执行的核验器。
if [ ! -f "${SRC}/SKILL.md" ] || [ ! -f "${SRC}/scripts/verify-quotes.py" ]; then
  echo "错误：${SRC} 缺少 SKILL.md 或 scripts/verify-quotes.py，无法安装。" >&2
  echo "请确认在完整的 lit-panel 仓库内运行本脚本。" >&2
  exit 1
fi

mkdir -p "${DEST_DIR}"

# 已存在同名目标时，先确认是否覆盖，避免静默覆盖用户的本地修改。
if [ -e "${DEST}" ]; then
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

cp -r "${SRC}" "${DEST}"

echo ""
echo "已安装：${SRC} -> ${DEST}"
echo ""
echo "验证指引："
echo "  1. 确认文件已就位：ls -la \"${DEST}\""
echo "  2. 确认 frontmatter 完整：head -n 5 \"${DEST}/SKILL.md\""
echo "  3. 确认核验器可执行：python3 \"${DEST}/scripts/verify-quotes.py\" --help"
echo "  4. 开一个新的 Codex 会话（已打开的会话不会重新扫描 skill 目录），"
echo "     让它评审一段中文回忆录/叙事文本片段，确认它能读取并遵循"
echo "     lit-panel 的判据文件与输出契约。"
echo "  5. Codex 没有并行 subagent 机制，十一席会按 SKILL.md 编排逐席"
echo "     顺序执行；这是预期行为，互盲语义与 Claude Code 并行执行等价。"
