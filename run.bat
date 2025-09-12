@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

rem 选择 Python 启动器
where py >nul 2>nul
if %errorlevel%==0 (
  set PY=py
) else (
  set PY=python
)

rem 创建虚拟环境（如不存在）
if not exist .venv\Scripts\python.exe (
  echo [INFO] Creating virtual environment .venv ...
  %PY% -m venv .venv
)

rem 安装依赖
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

rem 打开浏览器
start "" http://localhost:8000/

rem 启动后端服务（开发模式，自动重载）
".venv\Scripts\python.exe" -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload

endlocal