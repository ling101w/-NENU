#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# 选择可用的 Python 解释器
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[ERROR] 未找到 Python，请先安装 Python 3.8+" >&2
  exit 1
fi

# 创建虚拟环境（如不存在）
if [ ! -f .venv/bin/python ]; then
  echo "[INFO] Creating virtual environment .venv ..."
  "$PY" -m venv .venv
fi

# 安装依赖
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

# 尝试打开浏览器
URL="http://localhost:8000/"
if command -v xdg-open >/dev/null 2>&1; then
  (xdg-open "$URL" >/dev/null 2>&1 || true) &
elif command -v open >/dev/null 2>&1; then
  (open "$URL" >/dev/null 2>&1 || true) &
fi

# 启动后端服务（开发模式，自动重载）
exec ./.venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload