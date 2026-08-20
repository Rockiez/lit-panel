#!/usr/bin/env bash
# Install lit-panel from the generated Claude Code plugin distribution.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_ROOT="${REPO_ROOT}/dist/claude"
LIT_PANEL_VERSION="$(tr -d '[:space:]' < "${REPO_ROOT}/VERSION")"
REBUILD=false

for arg in "$@"; do
  case "${arg}" in
    --rebuild)
      REBUILD=true
      ;;
    -h|--help)
      echo "用法: $0 [--rebuild]"
      echo "  默认从仓库已提交的 dist/claude 安装，不执行构建。"
      echo "  --rebuild  维护者选项：安装前从 core/adapters 重新生成 dist。"
      exit 0
      ;;
    *)
      echo "未知参数: ${arg}" >&2
      exit 1
      ;;
  esac
done

if ! command -v claude >/dev/null 2>&1; then
  echo "错误：未找到 claude CLI。" >&2
  exit 1
fi

CLAUDE_VERSION="$(claude --version | awk '{print $1}')"
if ! python3 - "${CLAUDE_VERSION}" <<'PY'
import re
import sys

parts = tuple(int(value) for value in re.findall(r"\d+", sys.argv[1])[:3])
raise SystemExit(0 if parts >= (2, 1, 63) else 1)
PY
then
  echo "错误：当前 Claude Code ${CLAUDE_VERSION}，要求 >= 2.1.63（plugin + Agent）。" >&2
  exit 1
fi

if [ "${REBUILD}" = true ]; then
  python3 "${REPO_ROOT}/scripts/build_dist.py"
fi
for runtime in verify_quotes.py verify-quotes.py repair_quotes.py; do
  if [ ! -f "${DIST_ROOT}/skills/lit-panel/scripts/${runtime}" ]; then
    echo "错误：Claude 分发缺少阶段二运行脚本 ${runtime}；请使用完整 release checkout，维护者可加 --rebuild。" >&2
    exit 1
  fi
  python3 "${DIST_ROOT}/skills/lit-panel/scripts/${runtime}" --help >/dev/null
done
claude plugin validate --strict "${DIST_ROOT}"

MARKETPLACE_JSON="$(claude plugin marketplace list --json)"
if printf '%s' "${MARKETPLACE_JSON}" | python3 -c 'import json,os,sys; expected=os.path.realpath(sys.argv[1]); data=json.load(sys.stdin); item=next((x for x in data if x.get("name") == "lit-panel"), None); raise SystemExit(0 if item and item.get("source") == "directory" and os.path.realpath(item.get("path", "")) == expected else 1)' "${DIST_ROOT}"; then
  echo "Claude marketplace lit-panel 已注册；跳过重复注册。"
elif printf '%s' "${MARKETPLACE_JSON}" | python3 -c 'import json,sys; raise SystemExit(0 if any(x.get("name") == "lit-panel" for x in json.load(sys.stdin)) else 1)'; then
  echo "错误：Claude marketplace lit-panel 已存在，但来源不是当前 ${DIST_ROOT}。" >&2
  echo "为避免从旧来源安装，脚本已停止且未修改 marketplace；请确认后显式移除旧 marketplace 再重试。" >&2
  exit 1
else
  claude plugin marketplace add "${DIST_ROOT}"
  MARKETPLACE_JSON="$(claude plugin marketplace list --json)"
  if ! printf '%s' "${MARKETPLACE_JSON}" | python3 -c 'import json,os,sys; expected=os.path.realpath(sys.argv[1]); data=json.load(sys.stdin); item=next((x for x in data if x.get("name") == "lit-panel"), None); raise SystemExit(0 if item and item.get("source") == "directory" and os.path.realpath(item.get("path", "")) == expected else 1)' "${DIST_ROOT}"; then
    echo "错误：Claude marketplace 注册后来源未确认为当前 ${DIST_ROOT}。" >&2
    exit 1
  fi
fi

PLUGIN_STATE="$(claude plugin list --json | python3 -c 'import json,sys; expected=sys.argv[1]; item=next((x for x in json.load(sys.stdin) if x.get("id") == "lit-panel@lit-panel"), None); print("current" if item and item.get("version") == expected else "outdated" if item else "missing")' "${LIT_PANEL_VERSION}")"
case "${PLUGIN_STATE}" in
  current)
    echo "Claude Code plugin 已是 lit-panel@lit-panel ${LIT_PANEL_VERSION}；跳过重复安装。"
    ;;
  outdated)
    claude plugin update lit-panel@lit-panel
    ;;
  missing)
    claude plugin install lit-panel@lit-panel
    ;;
esac
if ! claude plugin list --json | python3 -c 'import json,sys; expected=sys.argv[1]; raise SystemExit(0 if any(x.get("id") == "lit-panel@lit-panel" and x.get("version") == expected for x in json.load(sys.stdin)) else 1)' "${LIT_PANEL_VERSION}"; then
  echo "错误：Claude Code plugin 安装后未达到 lit-panel@lit-panel ${LIT_PANEL_VERSION}。" >&2
  exit 1
fi

echo "已安装 Claude Code plugin：lit-panel@lit-panel"
