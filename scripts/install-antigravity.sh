#!/usr/bin/env bash
# Install the self-contained Antigravity plugin for CLI, IDE/global, or workspace.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_ROOT="${REPO_ROOT}/dist/antigravity"
MODE="cli"
WORKSPACE_ROOT="${PWD}"
FORCE=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --cli)
      MODE="cli"
      ;;
    --ide)
      MODE="ide"
      ;;
    --workspace)
      MODE="workspace"
      if [ "$#" -gt 1 ] && [[ "$2" != --* ]]; then
        WORKSPACE_ROOT="$2"
        shift
      fi
      ;;
    -y|--force)
      FORCE=true
      ;;
    -h|--help)
      echo "用法: $0 [--cli|--ide|--workspace [path]] [-y|--force]"
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      exit 1
      ;;
  esac
  shift
done

if [ "${MODE}" = "cli" ]; then
  if ! command -v agy >/dev/null 2>&1; then
    echo "错误：未找到 agy CLI。CLI 安装要求 Antigravity CLI >= 1.1.12。" >&2
    exit 1
  fi
  ANTIGRAVITY_VERSION="$(agy --version | awk '{print $NF}')"
  if ! python3 - "${ANTIGRAVITY_VERSION}" <<'PY'
import re
import sys

parts = tuple(int(value) for value in re.findall(r"\d+", sys.argv[1])[:3])
raise SystemExit(0 if parts >= (1, 1, 12) else 1)
PY
  then
    echo "错误：当前 Antigravity CLI ${ANTIGRAVITY_VERSION}，要求 >= 1.1.12（plugin + subagents）。" >&2
    exit 1
  fi
fi

python3 "${REPO_ROOT}/scripts/build_dist.py"
for verifier in verify_quotes.py verify-quotes.py; do
  if [ ! -f "${DIST_ROOT}/skills/lit-panel/scripts/${verifier}" ]; then
    echo "错误：Antigravity 分发缺少阶段二核验器 ${verifier}。" >&2
    exit 1
  fi
  python3 "${DIST_ROOT}/skills/lit-panel/scripts/${verifier}" --help >/dev/null
done

if [ "${MODE}" = "cli" ]; then
  agy plugin validate "${DIST_ROOT}"
  agy plugin install "${DIST_ROOT}"
  echo "已安装 Antigravity CLI plugin：lit-panel"
  exit 0
fi

if [ "${MODE}" = "workspace" ]; then
  DEST="${WORKSPACE_ROOT}/.agents/plugins/lit-panel"
else
  DEST="${HOME}/.gemini/config/plugins/lit-panel"
fi

if [ -e "${DEST}" ] && [ "${FORCE}" != true ]; then
  echo "错误：目标已存在：${DEST}。确认覆盖后用 --force。" >&2
  exit 1
fi
DEST_PARENT="$(dirname "${DEST}")"
mkdir -p "${DEST_PARENT}"
STAGING="$(mktemp -d "${DEST_PARENT}/.lit-panel.staging.XXXXXX")"
BACKUP=""
cleanup_install_staging() {
  if [ -d "${STAGING}" ]; then
    rm -rf "${STAGING}"
  fi
}
trap cleanup_install_staging EXIT
cp -R "${DIST_ROOT}/." "${STAGING}/"
if [ -e "${DEST}" ]; then
  BACKUP="$(mktemp -d "${DEST_PARENT}/.lit-panel.backup.XXXXXX")"
  rmdir "${BACKUP}"
  mv "${DEST}" "${BACKUP}"
fi
if ! mv "${STAGING}" "${DEST}"; then
  if [ -n "${BACKUP}" ] && [ -e "${BACKUP}" ]; then
    mv "${BACKUP}" "${DEST}" || {
      echo "严重错误：新插件切换失败，旧插件保留在 ${BACKUP}。" >&2
      exit 1
    }
  fi
  echo "错误：新插件切换失败；旧安装已恢复。" >&2
  exit 1
fi
if [ -n "${BACKUP}" ] && [ -e "${BACKUP}" ]; then
  rm -rf "${BACKUP}"
fi
trap - EXIT
echo "已安装 Antigravity ${MODE} plugin：${DEST}"
