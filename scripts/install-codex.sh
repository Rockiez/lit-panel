#!/usr/bin/env bash
# Install lit-panel as a Codex Agent Plugin. Optionally install project agent types.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_ROOT="${REPO_ROOT}/dist/codex"
LIT_PANEL_VERSION="$(tr -d '[:space:]' < "${REPO_ROOT}/VERSION")"
PROJECT_AGENTS=""
FORCE=false

for arg in "$@"; do
  case "${arg}" in
    --project-agents)
      PROJECT_AGENTS="${PWD}/.codex/agents"
      ;;
    -y|--force)
      FORCE=true
      ;;
    -h|--help)
      echo "用法: $0 [--project-agents] [-y|--force]"
      echo "  默认通过本地 marketplace 安装 Agent Plugin。"
      echo "  --project-agents 另外把 11 个生成的 Agent TOML 安装到当前项目。"
      exit 0
      ;;
    *)
      echo "未知参数: ${arg}" >&2
      exit 1
      ;;
  esac
done

if ! command -v codex >/dev/null 2>&1; then
  echo "错误：未找到 codex CLI。lit-panel 要求 Codex >= 0.147.0。" >&2
  exit 1
fi

CODEX_VERSION="$(codex --version | awk '{print $NF}')"
if ! python3 - "${CODEX_VERSION}" <<'PY'
import re
import sys

parts = tuple(int(value) for value in re.findall(r"\d+", sys.argv[1])[:3])
raise SystemExit(0 if parts >= (0, 147, 0) else 1)
PY
then
  echo "错误：当前 Codex ${CODEX_VERSION}，要求 >= 0.147.0（Agent Plugins + native subagents）。" >&2
  exit 1
fi

python3 "${REPO_ROOT}/scripts/build_dist.py"

codex_marketplace_path() {
  codex plugin marketplace list --json | python3 -c 'import json,sys; data=json.load(sys.stdin); print(next((x.get("root", "") for x in data.get("marketplaces", []) if x.get("name") == "lit-panel"), ""))'
}

restore_codex_marketplace() {
  local previous_path="$1"
  codex plugin marketplace remove lit-panel >/dev/null 2>&1 || true
  if ! codex plugin marketplace add "${previous_path}"; then
    echo "严重错误：切换 marketplace 失败，且无法恢复原路径 ${previous_path}。" >&2
    return 1
  fi
  local restored_path
  if ! restored_path="$(codex_marketplace_path)"; then
    echo "严重错误：恢复 marketplace 后无法读取注册状态；原路径为 ${previous_path}。" >&2
    return 1
  fi
  if [ "${restored_path}" != "${previous_path}" ]; then
    echo "严重错误：恢复 marketplace 后路径不一致；预期 ${previous_path}，实际 ${restored_path:-<missing>}。" >&2
    return 1
  fi
  echo "已恢复原 marketplace：${previous_path}" >&2
}

MARKETPLACE_PATH="$(codex_marketplace_path)"
if [ -n "${MARKETPLACE_PATH}" ] && [ "${MARKETPLACE_PATH}" != "${DIST_ROOT}" ]; then
  if [ "${FORCE}" != true ]; then
    echo "错误：marketplace lit-panel 已指向 ${MARKETPLACE_PATH}，目标为 ${DIST_ROOT}。确认切换后用 --force。" >&2
    exit 1
  fi
  PREVIOUS_MARKETPLACE_PATH="${MARKETPLACE_PATH}"
  codex plugin marketplace remove lit-panel
  if ! codex plugin marketplace add "${DIST_ROOT}"; then
    echo "错误：无法注册新 marketplace ${DIST_ROOT}；正在恢复原路径。" >&2
    restore_codex_marketplace "${PREVIOUS_MARKETPLACE_PATH}" || true
    exit 1
  fi
  if ! MARKETPLACE_PATH="$(codex_marketplace_path)"; then
    echo "错误：新 marketplace 注册后无法确认状态；正在恢复原路径。" >&2
    restore_codex_marketplace "${PREVIOUS_MARKETPLACE_PATH}" || true
    exit 1
  fi
  if [ "${MARKETPLACE_PATH}" != "${DIST_ROOT}" ]; then
    echo "错误：新 marketplace 注册后未通过路径确认；正在恢复原路径。" >&2
    restore_codex_marketplace "${PREVIOUS_MARKETPLACE_PATH}" || true
    exit 1
  fi
fi
if [ -z "${MARKETPLACE_PATH}" ]; then
  codex plugin marketplace add "${DIST_ROOT}"
  MARKETPLACE_PATH="$(codex_marketplace_path)"
  if [ "${MARKETPLACE_PATH}" != "${DIST_ROOT}" ]; then
    echo "错误：marketplace 注册后路径不一致；预期 ${DIST_ROOT}，实际 ${MARKETPLACE_PATH:-<missing>}。" >&2
    exit 1
  fi
fi

if codex plugin list --json | python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); raise SystemExit(0 if any(x.get("pluginId") == "lit-panel@lit-panel" and x.get("version") == expected for x in data.get("installed", [])) else 1)' "${LIT_PANEL_VERSION}"; then
  echo "Codex Agent Plugin 已是 lit-panel@lit-panel ${LIT_PANEL_VERSION}；跳过重复安装。"
else
  codex plugin add lit-panel@lit-panel --json
fi
if ! codex plugin list --json | python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); raise SystemExit(0 if any(x.get("pluginId") == "lit-panel@lit-panel" and x.get("version") == expected for x in data.get("installed", [])) else 1)' "${LIT_PANEL_VERSION}"; then
  echo "错误：Codex Agent Plugin 安装后未达到 lit-panel@lit-panel ${LIT_PANEL_VERSION}。" >&2
  exit 1
fi

if [ -n "${PROJECT_AGENTS}" ]; then
  mkdir -p "${PROJECT_AGENTS}"
  CONFLICTS=()
  for source in "${DIST_ROOT}"/.codex/agents/*.toml; do
    target="${PROJECT_AGENTS}/$(basename "${source}")"
    if [ -e "${target}" ]; then
      CONFLICTS+=("${target}")
    fi
  done
  if [ "${#CONFLICTS[@]}" -gt 0 ] && [ "${FORCE}" != true ]; then
    echo "错误：以下项目 Agent 定义已存在；未覆盖任何文件。确认备份并覆盖后用 --force：" >&2
    printf '  %s\n' "${CONFLICTS[@]}" >&2
    exit 1
  fi
  if [ "${#CONFLICTS[@]}" -gt 0 ]; then
    BACKUP_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
    BACKUP_DIR="${PROJECT_AGENTS}/.lit-panel-backup-${BACKUP_STAMP}-$$"
    mkdir -p "${BACKUP_DIR}"
    for target in "${CONFLICTS[@]}"; do
      cp -p "${target}" "${BACKUP_DIR}/"
    done
    echo "已备份 ${#CONFLICTS[@]} 个冲突 Agent 定义：${BACKUP_DIR}"
  fi
  cp "${DIST_ROOT}"/.codex/agents/*.toml "${PROJECT_AGENTS}/"
  echo "已安装项目 Agent 定义：${PROJECT_AGENTS}"
fi

echo "已安装 Codex Agent Plugin：lit-panel@lit-panel"
echo "请开启新 Codex task，确认 skill 发现并由原生 spawn_agent 派发席位。"
